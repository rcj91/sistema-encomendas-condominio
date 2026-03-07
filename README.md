# 📦 Sistema de Gestão de Encomendas para Condomínios

Sistema moderno para **registro, confirmação digital e notificação de encomendas** em portarias de condomínios — eliminando por completo a necessidade de assinatura em papel.

## 🚀 Problema Original

- Porteiro registra encomendas em livro físico
- Moradores precisam assinar papel para retirar
- Formação de filas na portaria
- Dificuldade para localizar encomendas
- Sem notificação — morador só descobre a encomenda quando vai à portaria
- Histórico difícil de consultar

## 💡 Solução (POC)

1. **Porteiro** registra a encomenda pelo sistema web
2. **Morador** recebe notificação por e-mail sobre a chegada
3. **Morador** acessa o sistema e faz a **confirmação digital** de retirada (sem papel!)
4. **Porteiro** vê em tempo real as confirmações e o status das encomendas
5. **Sistema** envia **lembretes automáticos por e-mail** diariamente para encomendas não retiradas
6. Todo o histórico fica registrado digitalmente

## 🧠 Funcionalidades

### Porteiro
- ✔ Login seguro com autenticação
- ✔ Registro de encomendas (apartamento, descrição, armário)
- ✔ Dashboard com encomendas pendentes e cores por tempo
- ✔ Busca e filtro por apartamento ou descrição
- ✔ Visualização de confirmações de retirada dos moradores
- ✔ Exportação de histórico CSV

### Morador
- ✔ Login seguro com autenticação
- ✔ Visualização das encomendas pendentes
- ✔ **Confirmação digital de retirada** (substitui assinatura em papel)
- ✔ Histórico pessoal de encomendas

### Sistema
- ✔ Notificação por e-mail ao registrar encomenda
- ✔ Lembretes automáticos diários para encomendas pendentes
- ✔ Senhas armazenadas com hash seguro
- ✔ Controle de sessão por papel (porteiro/morador)

## 🛠 Tecnologias

| Componente | Tecnologia |
|-----------|-----------|
| Backend | Python / Flask |
| Banco de Dados | SQLite |
| Frontend | HTML5 / Bootstrap 5 |
| Autenticação | Flask-Login + Werkzeug |
| E-mail | Flask-Mail |
| Agendamento | APScheduler |

## 🚀 Como Executar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar e-mail (opcional para POC)

Edite o arquivo `condominio_app/config.py` com as credenciais SMTP:

```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'seu-email@gmail.com'
MAIL_PASSWORD = 'sua-senha-de-app'
```

> Para o POC, o sistema funciona sem configuração de e-mail — os envios serão simulados no log.

### 3. Iniciar a aplicação

```bash
cd condominio_app
python app.py
```

O sistema cria automaticamente o banco de dados e um usuário porteiro padrão no primeiro acesso.

### 4. Acessar

| URL | Descrição |
|-----|-----------|
| http://localhost:5000/ | Login |
| http://localhost:5000/porteiro | Dashboard do Porteiro |
| http://localhost:5000/morador | Dashboard do Morador |

### Credenciais padrão (POC)

| Papel | Usuário | Senha |
|-------|---------|-------|
| Porteiro | porteiro | porteiro123 |
| Morador | 101 | morador123 |
| Morador | 102 | morador123 |
| Morador | 201 | morador123 |

## 📐 Arquitetura

Veja o documento completo em [ARCHITECTURE.md](ARCHITECTURE.md).

