# 📦 Sistema de Gestão de Encomendas para Condomínios

Sistema simples e eficiente para **registro, organização e retirada de encomendas em portarias de condomínios para substituir livro físico**.

A solução digitaliza o processo tradicional de controle em livros físicos, reduzindo filas, erros de registro e facilitando a rastreabilidade das entregas.

---

# 🚀 Problema

Em muitos condomínios, o controle de encomendas ainda é feito de forma manual:

- Porteiro registra encomendas em **livro físico**
- Moradores precisam **assinar para retirar**
- Formação de **filas na portaria**
- **Dificuldade para localizar encomendas**
- **Histórico difícil de consultar**

Esse processo é lento, sujeito a erros e pouco eficiente.

---

# 💡 Solução

Este sistema digitaliza todo o fluxo de gestão de encomendas:

1️⃣ Porteiro registra a encomenda no sistema  
2️⃣ Sistema registra data e armário automaticamente  
3️⃣ Morador consulta a encomenda via **QR Code**  
4️⃣ Morador digita o número do apartamento  
5️⃣ Sistema mostra **onde a encomenda está armazenada**  
6️⃣ Retirada rápida e registrada

---

# 🧠 Funcionalidades

✔ Registro de encomendas  
✔ Controle de **armários de armazenamento**  
✔ Consulta pelo morador via **QR Code único**  
✔ Sistema de cores por **tempo de permanência**  
✔ Histórico de encomendas  
✔ Exportação de relatório para **Excel / CSV**  
✔ Busca por apartamento ou descrição  
✔ Interface simples para porteiros  

---

# 📱 Fluxo do Sistema

Recebimento da encomenda
↓
Registro no sistema
↓
Armazenamento em armário
↓
Consulta via QR Code
↓
Retirada pelo morador
↓
Registro no histórico

---

# 🏢 Benefícios para o Condomínio

- Redução de filas na portaria
- Menos trabalho manual para porteiros
- Maior organização das encomendas
- Histórico digital completo
- Transparência para síndicos e administradoras
- Rastreabilidade de todas as entregas

---

# 🛠 Tecnologias Utilizadas

- **Python**
- **Flask**
- **SQLite**
- **HTML / Bootstrap**
- **QR Code**
- **Git / GitHub**

---

# 📂 Estrutura do Projeto

condominio_app
│
├── app.py
├── create_db.py
├── database.db
├── templates
│ ├── porteiro.html
│ ├── morador.html
│ └── consultar.html
│
├── static
│
└── README.md
