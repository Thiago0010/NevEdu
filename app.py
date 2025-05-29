from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = '123456'

# Conexão com o banco de dados
def conectar():
    return sqlite3.connect('database.db')

# Criar tabelas do banco
def criar_banco():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            ano_escolar TEXT,
            inicio_escolar TEXT,
            foto TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome TEXT,
            data_conclusao TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome TEXT,
            icone TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)
    conn.commit()
    conn.close()

# Página inicial (home)
@app.route('/')
def home():
    return render_template('home.html')

# Página de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        confirmar = request.form['confirmar']

        if senha != confirmar:
            flash('Senhas não coincidem!')
            return redirect(url_for('cadastro'))

        try:
            senha_hash = generate_password_hash(senha)
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha_hash))
            conn.commit()
            conn.close()
            flash('Cadastro realizado com sucesso! Faça login.')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('E-mail já cadastrado.')
            return redirect(url_for('cadastro'))

    return render_template('cadastro.html')

# Página de login
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    senha = request.form['senha']
    token = request.form.get('g-recaptcha-response')

    # Aqui você pode adicionar verificação do token com o Google se quiser usar reCAPTCHA

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, senha FROM usuarios WHERE email=?', (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[2], senha):
        session['usuario_id'] = user[0]
        session['usuario_nome'] = user[1]
        return redirect(url_for('dashboard'))
    else:
        flash('Email ou senha inválidos.')
        return redirect(url_for('index'))

# Página dashboard
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', nome=session['usuario_nome'])

# Página perfil
@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para acessar o perfil.')
        return redirect(url_for('index'))

    usuario_id = session['usuario_id']
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('SELECT nome, ano_escolar, inicio_escolar, foto FROM usuarios WHERE id=?', (usuario_id,))
    user = cursor.fetchone()

    if not user:
        flash('Usuário não encontrado.')
        return redirect(url_for('dashboard'))

    nome, ano_escolar, inicio_escolar, foto = user

    # Cálculo do progresso escolar
    try:
        hoje = datetime.now().date()
        inicio = datetime.strptime(inicio_escolar, '%Y-%m-%d').date()
        fim = datetime(inicio.year, 12, 20).date()
        dias_totais = (fim - inicio).days
        dias_passados = (hoje - inicio).days
        progresso = round((dias_passados / dias_totais) * 100) if dias_passados >= 0 else 0
        progresso = min(max(progresso, 0), 100)
    except:
        progresso = 0

    # Cursos concluídos
    cursor.execute('SELECT nome, data_conclusao FROM historico_cursos WHERE usuario_id=? ORDER BY data_conclusao DESC', (usuario_id,))
    historico_cursos = [{'nome': row[0], 'data_conclusao': datetime.strptime(row[1], '%Y-%m-%d')} for row in cursor.fetchall()]

    # Badges
    cursor.execute('SELECT nome, icone FROM badges WHERE usuario_id=?', (usuario_id,))
    badges = [{'nome': row[0], 'icone': row[1]} for row in cursor.fetchall()]

    conn.close()

    return render_template('perfil.html', nome=nome, ano=ano_escolar or 'Não informado', inicio_escolar=inicio_escolar or '', progresso=progresso, foto=foto, historico_cursos=historico_cursos, badges=badges)

# Atualizar perfil
@app.route('/perfil/atualizar', methods=['POST'])
def atualizar_perfil():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401

    data = request.json
    nome = data.get('nome')
    ano_escolar = data.get('ano_escolar')
    inicio_escolar = data.get('inicio_escolar')

    if not (nome and ano_escolar and inicio_escolar):
        return jsonify({'error': 'Dados incompletos'}), 400

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET nome=?, ano_escolar=?, inicio_escolar=? WHERE id=?',
                   (nome, ano_escolar, inicio_escolar, session['usuario_id']))
    conn.commit()
    conn.close()

    session['usuario_nome'] = nome
    return jsonify({'sucesso': True})

# Upload de foto
@app.route('/perfil/upload_foto', methods=['POST'])
def upload_foto():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401

    if 'foto' not in request.files:
        return jsonify({'error': 'Nenhuma foto enviada'}), 400

    foto = request.files['foto']
    if foto.filename == '':
        return jsonify({'error': 'Arquivo inválido'}), 400

    caminho = f'static/uploads/user_{session["usuario_id"]}.png'
    foto.save(caminho)

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET foto=? WHERE id=?', (caminho, session['usuario_id']))
    conn.commit()
    conn.close()

    return jsonify({'sucesso': True, 'caminho': caminho})

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Interface da IA
@app.route('/ia')
def ia():
    return render_template('ia.html')

# Resposta da IA (respostas predefinidas via JSON)
@app.route('/ia', methods=['POST'])
def ia_resposta():
    data = request.get_json()
    pergunta = data.get('pergunta', '').strip().lower()

    with open('data/respostas.json', encoding='utf-8') as f:
        respostas = json.load(f)

    resposta = respostas.get(pergunta, "Desculpe, ainda não sei responder isso 😢")

    return jsonify({'resposta': resposta})

# Inicializar o app
if __name__ == '__main__':
    criar_banco()
    app.run(debug=True)