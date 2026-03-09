# SwimRank — Balizamento Automático 🏊‍♂️

Sistema web para **gerenciamento de competições de natação escolar**: cadastro de alunos e provas, exportação de planilha de balizamento, upload de resultados e cálculo automático de ranking.

---

## ✨ Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| 📊 Dashboard | Ranking de equipes (por Ano Escolar) + resultados por prova |
| 📝 Cadastros | Cadastro e remoção de alunos e provas |
| 📤 Balizamento | Exporta planilha CSV pré-preenchida com todos os alunos |
| ⬆️ Upload | Drag-and-drop para envio da planilha com tempos preenchidos |

---

## 🚀 Como Rodar Localmente

### 1. Pré-requisitos
- Python 3.10+
- pip

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Iniciar o servidor

```bash
python app.py
```

Acesse: **http://localhost:5000**

---

## 📋 Fluxo de Uso

1. **Cadastros** → Adicione os alunos (nome, matrícula, ano escolar) e as provas.
2. **Balizamento** → Clique em *Exportar CSV* — a planilha já virá com Nome, Matrícula, Ano Escolar e Prova preenchidos.
3. Preencha as colunas **Minutos**, **Segundos** e **Centésimos** após as provas.
   - Para desclassificado/ausente: `9 / 99 / 99`
4. **Upload** → Arraste e solte a planilha preenchida.
5. **Dashboard** → Veja o ranking automático com pontuação calculada.

---

## ⚡ Regras de Negócio

- **Conversão de tempo:** `total = min × 60 + seg + cent ÷ 100`
- **DQ/Ausente:** tempo `9:99.99` → 0 pontos, sem colocação
- **Ranking:** agrupado por Prova + Ano Escolar (equipes não competem entre si)
- **Pontuação:**

| Colocação | Pontos |
|-----------|--------|
| 1º | 10 |
| 2º | 8 |
| 3º | 7 |
| 4º | 6 |
| 5º | 5 |
| 6º | 4 |
| 7º | 3 |
| 8º | 2 |
| 9º | 1 |

- **Empates:** mesmo tempo → mesma colocação → mesma pontuação

---

## ☁️ Deploy no Render.com (Gratuito)

1. Faça push do projeto para um repositório GitHub.
2. Acesse [render.com](https://render.com) e clique em **New Web Service**.
3. Conecte o repositório → Render detecta o `Procfile` automaticamente.
4. Defina a variável de ambiente `SECRET_KEY` com um valor seguro.
5. Clique em **Deploy** — pronto! 🎉

---

## 📁 Estrutura do Projeto

```
├── app.py                  # Entry point Flask
├── config.py               # Configurações
├── extensions.py           # Instância do SQLAlchemy
├── models.py               # Modelos: Student, Event, Result
├── requirements.txt
├── Procfile                # Deploy Render/Heroku
├── routes/
│   ├── dashboard.py
│   ├── cadastros.py
│   ├── balizamento.py
│   └── upload.py
├── services/
│   └── processor.py        # Lógica de ranking + pontuação
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── cadastros.html
│   ├── balizamento.html
│   └── upload.html
└── static/
    ├── css/style.css
    └── js/main.js
```
