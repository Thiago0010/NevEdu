from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3, json, requests

app = Flask(__name__)
app.secret_key = '123456'

# ---------- BANCO ----------
def conectar():
    return sqlite3.connect('database.db')

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
        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            descricao TEXT,
            imagem TEXT,
            autor TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS modulos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curso_id INTEGER,
            titulo TEXT NOT NULL,
            ordem INTEGER,
            FOREIGN KEY (curso_id) REFERENCES cursos(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modulo_id INTEGER,
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            ordem INTEGER,
            FOREIGN KEY (modulo_id) REFERENCES modulos(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cursos_gerados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            descricao TEXT,
            modulos TEXT,
            status TEXT DEFAULT 'pendente'
        )
    """)
    conn.commit()
    conn.close()

# ---------- HOME ----------
@app.route('/')
def home():
    return render_template('home.html')

# ---------- CADASTRO ----------
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
            flash('Cadastro realizado com sucesso!')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('E-mail já cadastrado.')
            return redirect(url_for('cadastro'))
    return render_template('cadastro.html')

@app.route('/index')
def index():
    return render_template('index.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    senha = request.form['senha']

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

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', nome=session['usuario_nome'])

# ---------- PERFIL ----------
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
    conn.close()

    if not user:
        flash('Usuário não encontrado.')
        return redirect(url_for('dashboard'))

    nome, ano_escolar, inicio_escolar, foto = user
    return render_template('perfil.html', nome=nome, ano=ano_escolar, inicio_escolar=inicio_escolar, foto=foto)

# ---------- CURSOS ----------
@app.route('/cursos')
def cursos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, descricao FROM cursos")
    cursos = cursor.fetchall()
    conn.close()
    return render_template('cursos.html', cursos=cursos)

@app.route('/curso/<int:curso_id>')
def curso_detalhe(curso_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, descricao, imagem, autor FROM cursos WHERE id = ?", (curso_id,))
    curso = cursor.fetchone()

    cursor.execute("SELECT id, titulo FROM modulos WHERE curso_id = ?", (curso_id,))
    modulos = cursor.fetchall()

    estrutura = []
    for modulo in modulos:
        cursor.execute("SELECT titulo, conteudo FROM licoes WHERE modulo_id = ?", (modulo[0],))
        licoes = cursor.fetchall()
        estrutura.append({
            'modulo': modulo[1],
            'licoes': licoes
        })

    conn.close()
    return render_template('curso_detalhe.html', curso=curso, estrutura=estrutura)

# ---------- IA GERADORA ----------
def pesquisar_resumo(texto):
    url = 'https://pt.wikipedia.org/api/rest_v1/page/summary/' + texto.replace(' ', '_')
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code == 200:
        data = r.json()
        return data.get("extract")
    return None

@app.route('/gerar_curso', methods=['GET', 'POST'])
def gerar_curso():
    if request.method == 'POST':
        ideia = request.form['ideia']
        resumo = pesquisar_resumo(ideia)

        if not resumo:
            resumo = "Não foi possível obter informações suficientes."

        modulos = [
            {"nome": "Módulo 1: Introdução", "conteudo": resumo},
            {"nome": "Módulo 2: Conceitos Essenciais", "conteudo": f"Conceitos fundamentais sobre {ideia}."},
            {"nome": "Módulo 3: Aplicações", "conteudo": f"Como aplicar {ideia} em situações reais."},
            {"nome": "Módulo 4: Avaliação", "conteudo": f"Teste seus conhecimentos sobre {ideia}."}
        ]

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cursos_gerados (titulo, descricao, modulos) VALUES (?, ?, ?)", 
                       (f"Curso: {ideia.title()}", resumo, json.dumps(modulos)))
        conn.commit()
        conn.close()
        flash('Curso gerado e enviado para avaliação!')
        return redirect(url_for('dashboard'))

    return render_template('gerar_curso.html')

# ---------- AVALIAÇÃO ----------
@app.route('/avaliar_cursos')
def avaliar_cursos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, descricao, modulos FROM cursos_gerados WHERE status='pendente'")
    cursos = cursor.fetchall()
    conn.close()
    cursos_dict = [
        {'id': c[0], 'titulo': c[1], 'descricao': c[2], 'modulos': c[3]}
        for c in cursos
    ]
    return render_template('avaliar_cursos.html', cursos=cursos_dict)

@app.route('/avaliar_curso/<int:id>/aceitar', methods=['POST'])
def aceitar_curso(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, descricao, modulos FROM cursos_gerados WHERE id=?", (id,))
    curso = cursor.fetchone()

    if curso:
        cursor.execute("INSERT INTO cursos (titulo, descricao, imagem, autor) VALUES (?, ?, '', 'IA')", 
                       (curso[0], curso[1]))
        cursor.execute("UPDATE cursos_gerados SET status='aprovado' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('avaliar_cursos'))

@app.route('/avaliar_curso/<int:id>/rejeitar', methods=['POST'])
def rejeitar_curso(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE cursos_gerados SET status='rejeitado' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('avaliar_cursos'))

@app.route('/avaliar_curso/<int:id>/deletar', methods=['POST'])
def deletar_curso(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cursos_gerados WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('avaliar_cursos'))
@app.route('/agenda')
def agenda():
    return render_template('agenda.html')

@app.route('/ia')
def ia():
    return render_template('ia.html')

@app.route('/Blog')
def Blog():
    return render_template('NevEdu-Blog.html')

@app.route('/termos')
def termos():
    return render_template('termos.html')
# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ---------- START ----------
if __name__ == '__main__':
    criar_banco()
    app.run(debug=True)
