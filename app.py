from flask import Flask, render_template, redirect, url_for, request, session
import mysql.connector
import random
import string
from flask_session import Session



app = Flask(__name__)

# A rechercher
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
Session(app)


db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'recommendation_system'
}


def get_db_connection():
    return mysql.connector.connect(**db_config)


def ensure_user():
    if 'user_id' not in session:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("INSERT INTO users (username) VALUES (%s)", ('user_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),))
        session['user_id'] = cursor.lastrowid
        connection.commit()
        
        cursor.close()
        connection.close()

def get_recommendations(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    
    query = query = """
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.image_url,
        COALESCE(v.visit_count, 0) AS visit_count,
        COALESCE(pr.purchase_count, 0) AS purchase_count
    FROM products p
    LEFT JOIN (
        SELECT product_id, SUM(visit_count) AS visit_count
        FROM visits
        WHERE user_id = %s
        GROUP BY product_id
    ) v ON p.product_id = v.product_id
    LEFT JOIN (
        SELECT product_id, SUM(purchase_count) AS purchase_count
        FROM purchases
        WHERE user_id = %s
        GROUP BY product_id
    ) pr ON p.product_id = pr.product_id
    """
    cursor.execute(query, (user_id, user_id))
    product_interactions = cursor.fetchall()

    
    for product in product_interactions:
        product['score'] = product['visit_count'] * 1 + product['purchase_count'] * 2

    
    category_scores = {}
    for product in product_interactions:
        if product['category'] not in category_scores:
            category_scores[product['category']] = 0
        category_scores[product['category']] += product['score']

    
    sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    
    if not sorted_categories or sorted_categories[0][1] == 0:
        cursor.close()
        connection.close()
        return []

    
    top_category = sorted_categories[0][0]
    second_category = sorted_categories[1][0] if len(sorted_categories) > 1 and sorted_categories[1][1] > 0 else None

    recommendations = []

    
    if top_category:
        cursor.execute("""
        SELECT product_id, product_name, image_url
        FROM products
        WHERE category = %s
        ORDER BY RAND()
        LIMIT 2
        """, (top_category,))
        recommendations.extend(cursor.fetchall())

    if second_category:
        cursor.execute("""
        SELECT product_id, product_name, image_url
        FROM products
        WHERE category = %s
        ORDER BY RAND()
        LIMIT 1
        """, (second_category,))
        recommendations.extend(cursor.fetchall())

    
    recommendations = recommendations[:3]

    cursor.close()
    connection.close()

    return recommendations






@app.route('/')
def index():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
   
    cursor.execute('SELECT product_id, product_name, image_url FROM products')
    products = cursor.fetchall()
    
    
    user_id = 1
    recommendations = get_recommendations(user_id)
    
    
    cursor.close()
    connection.close()
    
    return render_template('index.html', products=products, recommendations=recommendations)

@app.route('/product/<int:product_id>')
def product_page(product_id):
    ensure_user()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
   
    cursor.execute('SELECT product_id, product_name, image_url FROM products WHERE product_id = %s', (product_id,))
    
    
    
    product = cursor.fetchone()
    
    cursor.close()
    connection.close()
    
    return render_template('product.html', product=product)

@app.route('/visit/<int:product_id>')
def visit_product(product_id):
    ensure_user()
    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor()

    
    cursor.execute("SELECT * FROM visits WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    visit = cursor.fetchone()

    if visit:
        
        cursor.execute("UPDATE visits SET visit_count = visit_count + 1 WHERE user_id = %s AND product_id = %s",
                       (user_id, product_id))
    else:
        
        cursor.execute("INSERT INTO visits (user_id, product_id, visit_count) VALUES (%s, %s, 1)",
                       (user_id, product_id))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for('product_page', product_id=product_id))


@app.route('/purchase/<int:product_id>')
def purchase_product(product_id):
    ensure_user()
    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM purchases WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    purchase = cursor.fetchone()

    if purchase:
        
        cursor.execute("UPDATE purchases SET purchase_count = purchase_count + 1 WHERE user_id = %s AND product_id = %s",
                       (user_id, product_id))
    else:
        
        cursor.execute("INSERT INTO purchases (user_id, product_id, purchase_count) VALUES (%s, %s, 1)",
                       (user_id, product_id))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
