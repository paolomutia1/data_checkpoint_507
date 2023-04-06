import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request
from flask import send_from_directory
import os
from collections import defaultdict
from gevent.pywsgi import WSGIServer
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

search_history = []

class Book:
    """
    A class to represent a book.
    """
    def __init__(self, title="No Title", author="No Author", release_year="No Release Year", 
                 url="No URL", genres=None, average_rating=None, json=None):
        """
        Constructs all the necessary attributes for the Book object.

        Parameters
        ----------
        title : str, optional
            The title of the book (default "No Title")
        author : str, optional
            The author of the book (default "No Author")
        release_year : str, optional
            The release year of the book (default "No Release Year")
        url : str, optional
            The URL for the book (default "No URL")
        genres : list, optional
            A list of genres for the book (default empty list)
        average_rating : float, optional
            The average rating of the book (default None)
        json : dict, optional
            A JSON object containing book information (default None)
        """
        if json is not None:
            self.title = json["volumeInfo"].get("title", "No Title")
            self.author = ', '.join(json["volumeInfo"].get("authors", ["No Author"]))
            self.release_year = json["volumeInfo"].get("publishedDate", "No Release Year")[:4]
            self.url = json["volumeInfo"].get("previewLink", "No URL")
            self.genres = json["volumeInfo"].get("categories", [])
            self.average_rating = float(json["volumeInfo"].get("averageRating", 0))
        else:
            self.title = title
            self.author = author
            self.release_year = release_year
            self.url = url
            self.genres = genres or []
            self.average_rating = average_rating

    def info(self):
        """
        Returns a formatted string containing the book title, author, and release year.
        
        Returns
        -------
        str
            A string with the book title, author, and release year.
        """
        return f"{self.title} by {self.author} ({self.release_year})"


def search_books(query, api_key, max_results=10, start_index=0, lang=None, 
                 order_by=None, author=None, genre=None, min_rating=None):
    """
    Search for books using the Google Books API.

    Args
    -----
    query (str): The search query.
    api_key (str): The Google Books API key.
    max_results (int, optional): The maximum number of results to return. Defaults to 10.
    start_index (int, optional): The starting index of the search results. Defaults to 0.
    lang (str, optional): The language filter. Defaults to None.
    order_by (str, optional): The sorting order. Defaults to None.
    author (str, optional): The author filter. Defaults to None.
    genre (str, optional): The genre filter. Defaults to None.
    min_rating (float, optional): The minimum rating filter. Defaults to None.

    Returns
    --------
    tuple: A tuple containing a list of Book objects and the total number of items found.
    """
    # Create a cache directory if it doesn't exist
    cache_dir = 'cache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # Check if the data is already cached
    cache_file = os.path.join(cache_dir, f"{query}_{start_index}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            data = json.load(f)
    else:
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}&startIndex={start_index}&key={api_key}"
        if lang:
            url += f"&langRestrict={lang}"
        if order_by:
            url += f"&orderBy={order_by}"
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e
        data = json.loads(response.text)
        
        # Cache the data
        with open(cache_file, 'w') as f:
            json.dump(data, f)

    total_items = data.get("totalItems", 0)
    results = data.get("items", [])
    book_list = []
    for result in results:
        book = Book(json=result)
        book_list.append(book)

    # Apply filters
    if author or genre or min_rating:
        filtered_books = []
        for book in book_list:
            if author and author.lower() not in book.author.lower():
                continue
            if genre and genre not in book.genres:
                continue
            if min_rating and book.average_rating < min_rating:
                continue
            filtered_books.append(book)
        book_list = filtered_books

    return book_list, total_items

def search_movies(book_title, api_key):
    """
    Search for movies using the OMDb API.

    Args
    ----
    book_title (str): The search query.
    api_key (str): The OMDb API key.

    Returns
    -------
    list: A list of dictionaries containing movie information.
    """
    url = f"http://www.omdbapi.com/?apikey={api_key}&s={book_title}&type=movie"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise e
    data = json.loads(response.text)
    if data["Response"] == "True":
        results = data["Search"]
        movie_info = [{"Title": result["Title"], "imdbID": result["imdbID"]} for result in results]
        return movie_info
    else:
        return []
    
def search_articles(query, api_key, page=1, max_articles=10, lang=None):
    """
    Search for articles using the News API.

    Args:
        query (str): The search query.
        api_key (str): The News API key.
        page (int): The page number to fetch. Default is 1.
        max_articles (int): The maximum number of articles to return. Default is 10.
        lang (str): The language filter.

    Returns:
        list: A list of dictionaries containing article information.
    """
    url = f'https://newsapi.org/v2/everything?q={query}&apiKey={api_key}&page={page}'
    
    if lang:
        url += f"&language={lang}"

    response = requests.get(url)
    data = response.json()

    if 'articles' not in data:
        return []

    articles = []
    for article in data['articles']:
        articles.append({
            'title': article['title'],
            'url': article['url'],
            'source': article['source']['name'],
            'publishedAt': article['publishedAt']
        })

    articles = sorted(articles, key=lambda x: x['publishedAt'])

    return articles[:max_articles]

def create_genre_graph(book_list):
    """
    Create a genre graph from a list of Book objects.

    Args:
        book_list (list): A list of Book objects.

    Returns:
        dict: A dictionary containing genre as the key and a list of books as the value.
    """
    genre_graph = defaultdict(list)
    for book in book_list:
        for genre in book.genres:
            genre_graph[genre].append(book)
    return genre_graph

def find_most_common_genres(book_list):
    """
    Find the most common genres in a list of Book objects.

    Args:
        book_list (list): A list of Book objects.

    Returns:
        tuple: A tuple containing a list of the most common genres and a dictionary with genre as the key and a list of books as the value.
    """
    genre_graph = {}
    for book in book_list:
        for genre in book.genres:
            if genre not in genre_graph:
                genre_graph[genre] = []
            genre_graph[genre].append(book)
    most_common_genres = sorted(genre_graph.keys(), key=lambda x: len(genre_graph[x]), reverse=True)
    return most_common_genres, genre_graph


def find_highest_rated_books(book_list):
    """
    Find the highest-rated books in a list of Book objects.

    Args:
        book_list (list): A list of Book objects.

    Returns:
        list: A sorted list of books based on their average rating.
    """
    return sorted(book_list, key=lambda x: x.average_rating, reverse=True)

def get_movie_description(imdb_id):
    """
    Get the movie description from IMDb by IMDb ID.

    Args:
        imdb_id (str): The IMDb ID of the movie.

    Returns:
        str: A string containing the movie description.
    """
    url = f"https://www.imdb.com/title/{imdb_id}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise e

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the description tag
    description_tag = soup.find('span', {'data-testid': 'plot-xl', 'class': 'sc-5f699a2-2 cxqNYC'})
    
    if description_tag:
        description = description_tag.text.strip()
    else:
        description = "Description not found."

    return description

app = Flask(__name__)

@app.route('/')
def index():
    """
    Render the index.html template.

    Returns:
        str: The rendered template.
    """
    return render_template('index.html')

@app.route('/search', methods=['POST', 'GET'])
def search():
    """
    Search for books, movies, and news articles based on the user's input.

    Returns:
        str: The rendered results.html template.
    """
    movie_data = []  # Add this line

    if request.method == 'POST':
        user_input = request.form['search_term']
        lang_filter = request.form['language']
        order_by = request.form['sort']
        start_index = int(request.form.get('start_index', 0))
        author_filter = request.form['author']
        genre_filter = request.form['genre']
        min_rating_filter = float(request.form.get('min_rating')) if request.form.get('min_rating') != '' else 0
        search_history.append(user_input)
    else:
        user_input = request.args.get('query', '')
        lang_filter = request.args.get('language', '')
        order_by = request.args.get('sort', '')
        start_index = int(request.args.get('start_index', 0))
        author_filter = request.args.get('author', '')
        genre_filter = request.args.get('genre', '')
        min_rating_filter = float(request.args.get('min_rating', 0))

    # Get the current page for news articles
    current_page = int(request.form.get('current_page', 1))
    book_list, total_items = search_books(user_input, API_KEY, max_results=10, start_index=start_index, lang=lang_filter, order_by=order_by, author=author_filter, genre=genre_filter, min_rating=min_rating_filter)
    movie_data = search_movies(user_input, OMDB_API_KEY)
    # print("Movie Data:", movie_data)

    # Get movie descriptions
    movie_descriptions = []
    for movie in movie_data:
        description = get_movie_description(movie['imdbID'])
        movie_descriptions.append(description)

    news_articles = search_articles(user_input, NEWS_API_KEY, page=current_page, lang=lang_filter)
    most_common_genres, genre_graph = find_most_common_genres(book_list)
    highest_rated_books = find_highest_rated_books(book_list)
    zipped_movie_data = zip(movie_data, movie_descriptions)
    # print(list(zipped_movie_data))

    return render_template('results.html', book_list=book_list, zipped_movie_data=zipped_movie_data, movie_data=movie_data, 
                            movie_descriptions=movie_descriptions, most_common_genres=most_common_genres, 
                            genre_graph=genre_graph, highest_rated_books=highest_rated_books, 
                            search_history=search_history, user_input=user_input, lang_filter=lang_filter, 
                            order_by=order_by, start_index=start_index, total_items=total_items, news_articles=news_articles,
                            current_page=current_page)

@app.route('/favicon.ico')
def favicon():
    """
    Serve the favicon.ico file.

    Returns:
        The favicon.ico file.
    """
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY")  # Google Books API key
    OMDB_API_KEY = os.environ.get("OMDB_API_KEY")  # OMDB API key
    NEWS_API_KEY = os.environ.get("NEWS_API_KEY")  # News API key
    app.run(debug=True)


