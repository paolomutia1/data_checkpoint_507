# Book and Movie Search

This Flask-based web application allows users to search for books, movies, and related articles. It uses the Google Books API, OMDB API, News API, and web scraping techniques to fetch relevant information.

## Features

- Search books using the Google Books API
- Search movies using the OMDB API
- Scrape detailed movie descriptions from IMDb using BeautifulSoup
- Scrape related articles from a website
- Voice input for search queries using Web Speech API
- Analyze search results (most common genres, highest-rated books)
- Display search results in a user-friendly template using Bootstrap and Jinja2
- Toggle dark mode for better user experience
- Pagination for search results

## Installation and Setup

1. Clone the repository:

git clone https://github.com/paolomutia1/data_checkpoint_507.git

2. Change the working directory to the project directory:

cd data_checkpoint_507

3. Create a virtual environment:

python -m venv venv

4. Activate the virtual environment:

source venv/bin/activate # On Linux and macOS
venv\Scripts\activate # On Windows

5. Install the required packages:

pip install -r requirements.txt

6. Create a `.env` file in the project directory and add your API keys:

- GOOGLE_BOOKS_API_KEY=your_google_books_api_key
- OMDB_API_KEY=your_omdb_api_key
- NEWS_API_KEY=your_news_api_key

Replace `your_google_books_api_key`, `your_omdb_api_key`, and `your_news_api_key` with your actual API keys. To obtain the API keys, follow these instructions:

- Google Books API: [Getting a Google Books API key](https://developers.google.com/books/docs/v1/using#APIKey)

- OMDB API: [OMDb API - The Open Movie Database](https://www.omdbapi.com/apikey.aspx)

- News API: [News API - Get API Key](https://newsapi.org/register)

7. Run the Flask application:

export FLASK_APP=app.py # On Linux and macOS
set FLASK_APP=app.py # On Windows
flask run

8. Open your web browser and navigate to `http://127.0.0.1:5000/` to access the application.


