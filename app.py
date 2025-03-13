from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import uuid
import requests
import feedparser


def query_arxiv(search_query="all", max_results=10, start=0):
    base_url = 'http://export.arxiv.org/api/query?'
    params = {
        'search_query': search_query,
        'start': start,
        'max_results': max_results
    }
    response = requests.get(base_url, params=params)
    feed = feedparser.parse(response.text)
    papers = []
    for entry in feed.entries:
        papers.append({
            'id': entry.id.split('/')[-1],
            'title': entry.title,
            'summary': entry.summary,
            'link': entry.link
        })
    return papers



app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///arxiv.db'
db = SQLAlchemy(app)

# Define database models
class ReadingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    share_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    # You can add a user relationship if implementing authentication

class PaperEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    arxiv_id = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    reading_list_id = db.Column(db.Integer, db.ForeignKey('reading_list.id'), nullable=False)

# Create the DB tables
with app.app_context():
    db.create_all()



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form.get('query', 'all')
        return redirect(url_for('index', query=query, page=1))
    
    query = request.args.get('query', 'all')
    page = int(request.args.get('page', 1))
    start = (page - 1) * 10
    papers = query_arxiv(search_query=query, max_results=10, start=start)
    return render_template('index.html', papers=papers, query=query, page=page)


@app.route('/create_list', methods=['POST'])
def create_list():
    list_name = request.form.get('list_name')
    if list_name:
        new_list = ReadingList(name=list_name)
        db.session.add(new_list)
        db.session.commit()
        flash('Reading list created!', 'success')
        return redirect(url_for('view_list', share_id=new_list.share_id))
    flash('Please provide a list name.', 'danger')
    return redirect(url_for('index'))


@app.route('/list/<share_id>')
def view_list(share_id):
    reading_list = ReadingList.query.filter_by(share_id=share_id).first_or_404()
    papers = PaperEntry.query.filter_by(reading_list_id=reading_list.id).all()
    return render_template('reading_list.html', reading_list=reading_list, papers=papers)


@app.route('/add_paper/<share_id>', methods=['POST'])
def add_paper(share_id):
    reading_list = ReadingList.query.filter_by(share_id=share_id).first_or_404()
    arxiv_id = request.form.get('arxiv_id')
    title = request.form.get('title')
    summary = request.form.get('summary')
    if arxiv_id and title and summary:
        paper = PaperEntry(arxiv_id=arxiv_id, title=title, summary=summary, reading_list_id=reading_list.id)
        db.session.add(paper)
        db.session.commit()
        flash('Paper added to reading list!', 'success')
    else:
        flash('Missing paper details.', 'danger')
    return redirect(url_for('view_list', share_id=share_id))
