from itertools import product
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user





application = Flask(__name__) #Criação da aplicação Flask
application.config['SECRET_KEY'] = 'minha_chave_secreta' #Chave secreta para sessões
application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db' # Configuração do banco de dados SQLite

login_manager = LoginManager()
db = SQLAlchemy(application)
login_manager.init_app(application)
login_manager.login_view = 'login'
CORS(application) #Habilita o CORS para permitir requisições de diferentes origens

#Modelagem
#User com id, username and password

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)#Nuallable=False significa que o campo não pode ser vazio.
    cart = db.relationship('CartItem', backref='user', lazy=True)


#Produto com id, price, name and description

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) #Nuallable=False significa que o campo não pode ser vazio.
    price = db.Column(db.Float, nullable=False) # Tem quer ser float devido ao preço poder ter casas decimais.
    description = db.Column(db.Text, nullable=True) 

    """ Nullable=True significa que o campo pode ser vazio;
        Colocamos o db.Text para permitir descrições mais longas;
        Colocamos também o nuallable=True para permitir que o campo seja opcional.
    """

class CartItem(db.Model): #Itens do carrinho de compras
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)



#Autenticação
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@application.route('/', methods=['GET'])
def home():
    return jsonify({"message": "API funcionando!"})


#Rota para adicionar o login do usuário

@application.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first() #Busca o usuário no banco de dados pelo nome de usuário.

    if user and data.get('password') == user.password:
        login_user(user) #Loga o usuário
        return jsonify({"message":"Logged in successfully."})
    return jsonify({"message":"Unauthorized. Invalid credentials."}), 401

#Rota para logout do usuário

@application.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message":"Logout successfully."})




@application.route('/api/products/add', methods=['POST']) #Rota para adicionar um produto
@login_required
def add_product():
    data = request.json
    if "name" in data and "price" in data:
        product = Product(name=data["name"], price=data["price"], description=data.get("description", ""))
        db.session.add(product)
        db.session.commit()
        return jsonify({"message": "Produto adicionado com sucesso."})
    return jsonify({"error": "Nome e preço são obrigatórios."}), 400

@application.route('/api/products/delete/<int:product_id>', methods=['DELETE']) #Rota para deletar um produto
@login_required
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": "Produto deletado com sucesso."})
    return jsonify({"error": "Produto não encontrado."}), 404

@application.route('/api/products/<int:product_id>', methods=['GET']) #Rota para obter detalhes de um produto
def get_product_details(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description
        })
    return jsonify({"error": "Produto não encontrado."}), 404

@application.route('/api/products/update/<int:product_id>', methods=['PUT']) #Rota para atualizar um produto
@login_required
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Produto não encontrado."}), 404

    data = request.json
    if "name" in data:
        product.name = data["name"]

    if "price" in data:
        product.price = data["price"]

    if "description" in data:
        product.description = data["description"]

    db.session.commit()
    return jsonify({"message": "Produto atualizado com sucesso."})

@application.route('/api/products', methods=['GET']) #Rota para listar todos os produtos
def get_products():
    products = Product.query.all()
    products_list = []
    for product in products:
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price
        }
        products_list.append(product_data)
    return jsonify(products_list)


#Checkout

@application.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    user = User.query.get(int(current_user.id))
    product = Product.query.get(product_id)
    
    if user and product:
        cart_item = CartItem(user_id=user.id, product_id=product.id)
        db.session.add(cart_item)
        db.session.commit()
        return jsonify({"message": "Produto adicionado ao carrinho."})
    return jsonify({"error": "Usuário ou produto não encontrado."}), 400


@application.route('/api/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required
def remove_from_cart(product_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"message": "Produto removido do carrinho."})
    return jsonify({"error": "Produto não encontrado no carrinho."}), 400
    

@application.route('/api/cart', methods=['GET'])
@login_required
def view_cart():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    cart_content = []
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        cart_content.append({
                                "id": cart_item.id,
                                "user_id": cart_item.user_id,
                                "product_id": cart_item.product_id,
                                "product_name": product.name,
                                "product_price": product.price
                            })
    return jsonify(cart_content)


@application.route('/api/cart/checkout', methods=['POST'])
@login_required
def checkout():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    for cart_item in cart_items:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"messagem": "Checkout successful. Cart has been cleared."})
    

# Cria o banco e tabelas na inicialização (só roda uma vez)
with application.app_context():
    db.create_all()
    
    # Cria um usuário admin padrão se não existir
    if not User.query.filter_by(username='yoshi').first():
        admin = User(username='yoshi', password='12345')
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado: yoshi/12345")
    else:
        print("Usuário admin já existe.")

if __name__ == "__main__":
     application.run(debug=True)