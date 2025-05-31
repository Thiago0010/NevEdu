# 🎓 NevEdu

NevEdu é uma plataforma educacional full-stack voltada para alunos e professores, com o objetivo de democratizar o aprendizado por meio da tecnologia. Com uma interface moderna, recursos interativos e uma assistente virtual integrada, o projeto busca transformar a forma como os estudantes aprendem — e os professores ensinam.

---

## 🚀 Funcionalidades Principais

- ✅ Sistema de cadastro e login com proteção de senha
- ✅ Dashboard personalizado por usuário
- ✅ Perfil com progresso automatizado com base no ano escolar
- ✅ Upload e visualização de foto de perfil
- ✅ Histórico de cursos e conquistas (badges)
- ✅ Página de recomendações de conteúdo
- ✅ Interface com assistente virtual (IA)
- ✅ Front-end responsivo e escuro/claro com animações suaves

---

## 🤖 Assistente Virtual (IA)

A IA é alimentada por respostas pré-definidas, com fallback para buscas externas simplificadas (simuladas por enquanto). Ela responde dúvidas, ajuda no aprendizado e simula uma conversa direta com o aluno.

---

## 🛠️ Tecnologias Utilizadas

- **Python** + **Flask** (Back-end)
- **SQLite3** (Banco de Dados)
- **HTML5 / CSS3 / JavaScript** (Front-end)
- **Jinja2** (Templates dinâmicos)
- **Google reCAPTCHA v2** (Verificação no login)
- **JSON** (Base de respostas da IA)

---

## 🧩 Estrutura de Pastas

NevEdu/
│
├── static/
│ ├── css/
│ └── uploads/
│
├── templates/
│ ├── index.html
│ ├── cadastro.html
│ ├── dashboard.html
│ ├── perfil.html
│ └── ia.html
│
├── data/
│ └── respostas.json
│
├── app.py
└── database.db

yaml
Copiar
Editar

---

## 📦 Como Executar Localmente

1. Clone o repositório:
   ```bash
   git clone https://github.com/Thiago0010/NevEdu.git
   cd NevEdu
Instale as dependências:

bash
Copiar
Editar
pip install flask werkzeug
Execute o projeto:

bash
Copiar
Editar
python app.py
Acesse:

arduino
Copiar
Editar
http://localhost:5000
🧠 Inspiração
Inspirado por plataformas como Origamid, AtlasEdu, e o desejo de criar algo que una aprendizado, acessibilidade e tecnologia em um só lugar.

📌 Observações
A IA ainda está em fase experimental.

O design e funcionalidades estão em constante evolução.

Todo o projeto está sendo desenvolvido de forma independente.

🙌 Feito com fé e café por Thiago0010
