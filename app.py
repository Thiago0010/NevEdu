from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3, json, requests
from jinja2 import Environment

app = Flask(__name__)
app.secret_key = '123456'

app.jinja_env.filters['loads'] = json.loads

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
            tipo TEXT NOT NULL DEFAULT 'aluno',
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
        tipo = request.form.get('tipo', 'aluno')  # ← padrão é aluno

        if senha != confirmar:
            flash('Senhas não coincidem!')
            return redirect(url_for('cadastro'))

        try:
            senha_hash = generate_password_hash(senha)
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)',
                (nome, email, senha_hash, tipo)
            )
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
    cursor.execute('SELECT id, nome, senha, tipo FROM usuarios WHERE email=?', (email,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        flash('Email não encontrado.')
        return redirect(url_for('index'))

    if not check_password_hash(user[2], senha):
        flash('Senha incorreta.')
        return redirect(url_for('index'))

    session['usuario_id'] = user[0]
    session['usuario_nome'] = user[1]
    session['usuario_tipo'] = user[3]

    if user[3] == 'professor':
        return redirect(url_for('professor'))
    else:
        return redirect(url_for('dashboard'))

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

# ---------- ROTAS COMPLEMENTARES ----------
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

@app.route('/Professores')
def professor():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('professor.html', nome=session['usuario_nome'])

@app.route('/Alunos')
def alunos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email, foto FROM usuarios WHERE tipo = 'aluno'")
    dados = cursor.fetchall()
    conn.close()

    cores = ['normal', 'c-claro', 'c-esc']
    alunos = []
    for i, aluno in enumerate(dados):
        alunos.append({
            'id': aluno[0],
            'nome': aluno[1],
            'email': aluno[2],
            'foto': aluno[3] or '/static/img/user-default.png',
            'cor': cores[i % 3]
        })

    return render_template('aluno.html', alunos=alunos)

@app.route('/aluno/<int:aluno_id>')
def perfil_aluno(aluno_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, email, foto FROM usuarios WHERE id=?", (aluno_id,))
    aluno = cursor.fetchone()
    conn.close()

    if aluno:
        return render_template('aluno_individual.html', nome=aluno[0], email=aluno[1], foto=aluno[2])
    else:
        flash("Aluno não encontrado.")
        return redirect(url_for('alunos'))

@app.route('/Aulas')
def Aulas():
    return render_template('Aulas.html')

@app.route('/Tutoriais')
def Tutoriais():
    return render_template('tutoriais.html')

@app.route('/Atividades')
def Atividades():
    return render_template('atividades.html')

@app.route('/GerarCursos')
def Gerarcursos():
    return render_template('gerar_curso.html')

@app.route('/CursosCriados')
def CursosCriados():
    return render_template('cursos_criados.html')

@app.route('/Feedback-IA')
def Feedback():
    return render_template('feedback.html')

@app.route('/Visitas-IA')
def Visitas():
    return render_template('visitas.html')

@app.route('/Conteudo-semanal')
def Contsemanal():
    return render_template('conteudo_semanal.html')

@app.route('/Avisos')
def Avisos():
    return render_template('avisos.html')

def foto_aluno():
    return render_template('foto.html')
# ---------- 404 CUSTOM PAGE ----------
def nome():
    return render_template('erro.html')

@app.errorhandler(404)
def pagina_nao_encontrada(error):
    return render_template('erro.html'), 404
# ---------- START ----------
if __name__ == '__main__':
    criar_banco()
    app.run(debug=True)
