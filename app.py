from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import json
import requests

app = Flask(__name__)
app.secret_key = '123456'

# -------------------------
# BANCO DE DADOS
# -------------------------
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
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

    conn.commit()
    conn.close()

# -------------------------
# ROTAS BÁSICAS
# -------------------------
@app.route('/')
def home():
    return render_template('home.html')

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

@app.route('/index')
def index():
    return render_template('index.html')

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

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', nome=session['usuario_nome'])

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

    cursor.execute('SELECT nome, data_conclusao FROM historico_cursos WHERE usuario_id=? ORDER BY data_conclusao DESC', (usuario_id,))
    historico_cursos = [{'nome': row[0], 'data_conclusao': datetime.strptime(row[1], '%Y-%m-%d')} for row in cursor.fetchall()]

    cursor.execute('SELECT nome, icone FROM badges WHERE usuario_id=?', (usuario_id,))
    badges = [{'nome': row[0], 'icone': row[1]} for row in cursor.fetchall()]

    conn.close()

    return render_template('perfil.html', nome=nome, ano=ano_escolar or 'Não informado', inicio_escolar=inicio_escolar or '', progresso=progresso, foto=foto, historico_cursos=historico_cursos, badges=badges)

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

# -------------------------
# PESQUISA WIKIPEDIA
# -------------------------
def pesquisar_wikipedia(pergunta):
    try:
        search_url = 'https://pt.wikipedia.org/w/api.php'
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': pergunta,
            'format': 'json',
            'utf8': 1,
            'srlimit': 1
        }
        resp = requests.get(search_url, params=params, headers={'User-Agent': 'Mozilla/5.0'})
        data = resp.json()
        resultados = data.get('query', {}).get('search', [])
        if not resultados:
            return None
        titulo = resultados[0]['title']

        resumo_url = 'https://pt.wikipedia.org/api/rest_v1/page/summary/' + titulo.replace(' ', '_')
        resumo_resp = requests.get(resumo_url, headers={'User-Agent': 'Mozilla/5.0'})
        if resumo_resp.status_code != 200:
            return None
        resumo_json = resumo_resp.json()
        texto = resumo_json.get('extract', None)
        if texto:
            return texto
        return None
    except Exception as e:
        print(f"Erro ao pesquisar Wikipedia: {e}")
        return None

# -------------------------
# IA INTERATIVA (PERGUNTA E RESPOSTA)
# -------------------------
@app.route('/ia')
def ia():
    return render_template('ia.html')

@app.route('/ia', methods=['POST'])
def ia_resposta():
    data = request.get_json()
    pergunta = data.get('pergunta', '').strip().lower()

    # Respostas pré-definidas em JSON
    try:
        with open('data/respostas.json', encoding='utf-8') as f:
            respostas = json.load(f)
    except Exception:
        respostas = {}

    # Saudações simples
    saudações = {
        'oi': 'Oi! Como posso ajudar você hoje?',
        'olá': 'Olá! Em que posso ajudar?',
        'tudo bem?': 'Tudo ótimo! E com você?',
        'bom dia': 'Bom dia! Espero que tenha um ótimo dia!',
        'boa tarde': 'Boa tarde! Como posso ajudar?',
        'boa noite': 'Boa noite! Pronto para aprender algo novo?'
    }

    if pergunta in respostas:
        return jsonify({'resposta': respostas[pergunta]})
    elif pergunta in saudações:
        return jsonify({'resposta': saudações[pergunta]})

    # Pesquisa no Wikipedia como fallback para qualquer pergunta
    resposta_wiki = pesquisar_wikipedia(pergunta)
    if resposta_wiki:
        return jsonify({'resposta': resposta_wiki})

    # Resposta padrão caso nada seja encontrado
    return jsonify({'resposta': 'Ainda estou aprendendo sobre isso! Mas pode tentar reformular sua pergunta para eu entender melhor. 😉'})

# -------------------------
# LOGOUT
# -------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -------------------------
# TERMOS DE USO
# -------------------------
@app.route('/termos')
def termos():
    return render_template('termos.html')
# -------------------------
# TERMOS DE TERROR
# -------------------------
@app.route('/agenda')
def agenda():
    # lógica da agenda aqui, pode renderizar um template
    return render_template('agenda.html')

@app.route('/blog')
def Blog():
    # lógica da agenda aqui, pode renderizar um template
    return render_template('NevEdu-Blog.html')

@app.route('/Professores')
def professor():
 return render_template('professor.html')

@app.route('/cursos')
def cursos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, descricao, imagem FROM cursos")
    cursos = cursor.fetchall()
    conn.close()
    return render_template('cursos.html', cursos=cursos)

@app.route('/curso/<int:curso_id>')
def curso_detalhe(curso_id):
    conn = conectar()
    cursor = conn.cursor()

    # Curso principal
    cursor.execute("SELECT titulo, descricao, imagem, autor FROM cursos WHERE id = ?", (curso_id,))
    curso = cursor.fetchone()

    if not curso:
        return "Curso não encontrado", 404

    # Módulos
    cursor.execute("SELECT id, titulo FROM modulos WHERE curso_id = ? ORDER BY ordem", (curso_id,))
    modulos = cursor.fetchall()

    # Lição por módulo
    estrutura = []
    for modulo in modulos:
        cursor.execute("SELECT titulo, conteudo FROM licoes WHERE modulo_id = ? ORDER BY ordem", (modulo[0],))
        licoes = cursor.fetchall()
        estrutura.append({
            'modulo': modulo[1],
            'licoes': licoes
        })

    conn.close()

    return render_template('curso_detalhe.html', curso=curso, estrutura=estrutura)

# -------------------------
# INICIA A APLICAÇÃO
# -------------------------
if __name__ == '__main__':
    criar_banco()  # <- ESSENCIAL para evitar o erro de tabela
    app.run(debug=True)
