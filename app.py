from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, Response
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
        session['usuario_tipo'] = user[3]
    if user[3] == 'professor':
     return redirect(url_for('painel_professor'))
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

# The custom 404 HTML page content
custom_404_html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>NevEdu - Página não encontrada (Erro 404)</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

  /* Reset and base */
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
  html, body {
    height: 100%;
    font-family: 'Poppins', sans-serif;
    background: linear-gradient(135deg, #4A90E2, #50E3C2);
    color: #fff;
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
    overflow-x: hidden;
    padding: 20px;
  }

  .container {
    background: rgba(255 255 255 / 0.1);
    border-radius: 20px;
    padding: 40px 50px;
    max-width: 500px;
    box-shadow: 0 25px 40px rgba(0,0,0,0.25);
    backdrop-filter: blur(12px);
    position: relative;
    animation: fadeUp 0.8s ease forwards;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 480px;
  }

  @keyframes fadeUp {
    from {
      opacity: 0;
      transform: translateY(40px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .logo {
    font-weight: 900;
    font-size: 2.5rem;
    color: #ffffffdd;
    letter-spacing: 4px;
    margin-bottom: 35px;
    user-select: none;
    font-family: 'Poppins', sans-serif;
  }

  .error-code {
    font-size: 9rem;
    font-weight: 900;
    color: #fff;
    text-shadow:
      0 0 10px #50e3c233,
      0 0 20px #50e3c244,
      0 0 30px #4A90E2aa,
      0 0 40px #4A90E2cc;
    margin-bottom: 10px;
  }

  .error-message {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 25px;
    color: #e0f7fa;
  }

  .error-description {
    font-size: 1rem;
    line-height: 1.5;
    margin-bottom: 40px;
    color: #c9f0f7;
    max-width: 420px;
  }

  .btn-home {
    display: inline-block;
    padding: 14px 42px;
    font-size: 1.1rem;
    font-weight: 700;
    color: #4A90E2;
    text-decoration: none;
    border-radius: 50px;
    background: white;
    box-shadow: 0 8px 30px rgba(80,227,194,0.54);
    transition: all 0.3s ease;
    letter-spacing: 1.3px;
    margin-bottom: 45px;
  }

  .btn-home:hover,
  .btn-home:focus {
    background: #50e3c2;
    color: #fff;
    box-shadow: 0 12px 40px rgba(80,227,194,0.8);
    transform: translateY(-4px);
    outline: none;
  }

  .illustration {
    margin: 0 auto;
    width: 140px;
    height: 140px;
    position: relative;
    filter: drop-shadow(0 10px 10px rgba(0,0,0,0.12));
  }

  /* Animated book svg */
  .book-animation path {
    stroke: #50e3c2;
    stroke-width: 2.5;
    fill: none;
    stroke-linejoin: round;
    stroke-linecap: round;
    animation: dash 4s ease-in-out infinite alternate;
  }

  /* Animate dash offset for subtle stroke movement */
  @keyframes dash {
    0% {
      stroke-dasharray: 1500;
      stroke-dashoffset: 0;
    }
    50% {
      stroke-dasharray: 1500;
      stroke-dashoffset: -750;
    }
    100% {
      stroke-dasharray: 1500;
      stroke-dashoffset: 0;
    }
  }

  /* Footer small tagline */
  .footer-tagline {
    margin-top: 15px;
    font-size: 0.9rem;
    font-weight: 500;
    color: #a2e2d1;
    user-select: none;
  }

  /* Responsive */
  @media (max-width: 520px) {
    .container {
      max-width: 100%;
      padding: 30px 25px;
      min-height: auto;
    }
    .error-code {
      font-size: 6rem;
    }
    .logo {
      font-size: 2rem;
      margin-bottom: 25px;
    }
    .error-description {
      max-width: 100%;
    }
  }

</style>
</head>
<body>
  <div class="container" role="main" aria-labelledby="error-title" aria-describedby="error-desc">
    <div class="logo" aria-label="Logo do site NevEdu">NevEdu</div>
    <div class="error-code" id="error-title">404</div>
    <div class="error-message" id="error-desc">Ops! Página não encontrada.</div>
    <div class="error-description">
      A página que você está procurando pode ter sido removida,<br>teve o nome alterado ou está temporariamente indisponível.<br>Vamos te ajudar a voltar para o aprendizado!
    </div>
    <a href="/" class="btn-home" role="button" aria-label="Voltar para a página inicial do NevEdu">Voltar para a Página Inicial</a>

    <div class="illustration" aria-hidden="true">
      <svg class="book-animation" width="140" height="140" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
        <path d="M12 50V14a4 4 0 014-4h6v40h-6a4 4 0 01-4-4z"/>
        <path d="M28 10h21a4 4 0 014 4v32a4 4 0 01-4 4H28V10z"/>
        <path d="M43 26h-7" stroke="#50e3c2" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M43 34h-7" stroke="#50e3c2" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M43 42h-7" stroke="#50e3c2" stroke-width="2.5" stroke-linecap="round"/>
      </svg>
    </div>

    <div class="footer-tagline">NevEdu - Aprendizado que transforma</div>
  </div>
</body>
</html>
"""
@app.errorhandler(404)
def page_not_found(e):
    return Response(custom_404_html, status=404, mimetype='text/html')

tipo = request.form['tipo']  # adicionar isso no cadastro


# ---------- START ----------
if __name__ == '__main__':
    criar_banco()
    app.run(debug=True)
    