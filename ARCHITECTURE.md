# 📐 Arquitetura — Sistema de Encomendas para Condomínios

## 1. Análise da Versão Anterior

### ✅ Pontos Fortes

| Ponto | Descrição |
|-------|-----------|
| Simplicidade | Aplicação leve com Flask + SQLite, fácil de rodar |
| QR Code | Acesso rápido pelo morador via QR Code individual |
| Cores por tempo | Dashboard com cores indicando tempo de permanência (verde/amarelo/vermelho) |
| CSV Export | Exportação de histórico para Excel/CSV |
| Bootstrap | Interface responsiva e amigável |

### ❌ Pontos Fracos

| Ponto | Descrição |
|-------|-----------|
| Sem autenticação | Qualquer pessoa com o URL pode acessar o sistema |
| Senhas em texto puro | Senhas armazenadas sem hash no banco de dados |
| Sem notificação | Morador não sabe que tem encomenda até ir à portaria |
| Assinatura em papel | Retirada ainda requer processo manual |
| Sem confirmação digital | Porteiro marca retirada sem confirmação do morador |
| Sem e-mail | Sem comunicação automática com moradores |
| Sem separação de papéis | Porteiro e morador acessam as mesmas rotas |
| Sem migrações | Scripts manuais para alterar schema do banco |
| Debug em produção | `app.run(debug=True)` habilitado |
| Sem testes | Nenhum teste automatizado |
| Sem requirements.txt | Dependências não documentadas |

---

## 2. Nova Arquitetura (POC)

### Visão Geral

```
┌─────────────────────────────────────────────────────────┐
│                    NAVEGADOR WEB                        │
│                                                         │
│  ┌──────────────┐         ┌──────────────────────────┐  │
│  │   PORTEIRO   │         │        MORADOR           │  │
│  │  - Login     │         │  - Login                 │  │
│  │  - Registrar │         │  - Ver encomendas        │  │
│  │  - Dashboard │         │  - Confirmar retirada    │  │
│  │  - Histórico │         │  - Histórico pessoal     │  │
│  └──────┬───────┘         └──────────┬───────────────┘  │
│         │                            │                  │
└─────────┼────────────────────────────┼──────────────────┘
          │          HTTPS             │
┌─────────┼────────────────────────────┼──────────────────┐
│         ▼         FLASK APP          ▼                  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │              AUTENTICAÇÃO (Flask-Login)          │    │
│  │         Controle de sessão por papel             │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    ROTAS     │  │   MODELOS    │  │   E-MAIL     │  │
│  │  /porteiro/* │  │   User       │  │  Flask-Mail  │  │
│  │  /morador/*  │  │   Package    │  │  Notificação │  │
│  │  /auth/*     │  │              │  │  Lembrete    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
│  ┌──────┴─────────────────┴──────────────────┴───────┐  │
│  │               SQLite (database.db)                │  │
│  │  users: id, username, password_hash, role, email  │  │
│  │  packages: id, apartment, description, locker,    │  │
│  │           arrival_date, pickup_date, status,      │  │
│  │           confirmed_by, confirmed_at              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │          SCHEDULER (APScheduler)                  │  │
│  │    Lembrete diário para encomendas pendentes      │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Fluxo Principal

```
PORTEIRO                          SISTEMA                          MORADOR
   │                                 │                                │
   │  1. Registra encomenda          │                                │
   ├────────────────────────────────>│                                │
   │                                 │  2. Envia e-mail de chegada    │
   │                                 ├───────────────────────────────>│
   │                                 │                                │
   │                                 │  3. Morador faz login          │
   │                                 │<───────────────────────────────┤
   │                                 │                                │
   │                                 │  4. Confirma retirada digital  │
   │                                 │<───────────────────────────────┤
   │                                 │                                │
   │  5. Vê confirmação no dashboard │                                │
   │<────────────────────────────────┤                                │
   │                                 │                                │
   │                                 │  [Diário] Se não confirmou:    │
   │                                 │  6. Envia lembrete por e-mail  │
   │                                 ├───────────────────────────────>│
```

---

## 3. Estrutura de Arquivos

```
condominio_app/
├── app.py              # Aplicação Flask principal + rotas
├── models.py           # Modelos de banco de dados (User, Package)
├── config.py           # Configurações (DB, Mail, Secret Key)
├── email_service.py    # Serviço de envio de e-mails
├── scheduler.py        # Agendador de tarefas (lembretes diários)
├── templates/
│   ├── base.html       # Template base com navbar e layout
│   ├── login.html      # Página de login unificada
│   ├── porteiro/
│   │   └── dashboard.html  # Dashboard do porteiro
│   └── morador/
│       └── dashboard.html  # Dashboard do morador
└── tests/
    └── test_app.py     # Testes automatizados
```

---

## 4. Decisões Técnicas

### Por que manter Flask + SQLite?

- **POC**: Para validação rápida de conceito, não precisamos de infraestrutura complexa
- **Simplicidade**: Qualquer desenvolvedor consegue rodar em 2 minutos
- **Custo zero**: Sem necessidade de servidor de banco de dados ou serviços externos

### Por que Flask-Login?

- Gerenciamento de sessão pronto e seguro
- Suporte a papéis (porteiro/morador) com decoradores simples
- Integração nativa com Flask

### Por que Flask-Mail?

- Integração simples com qualquer servidor SMTP
- Suporte a Gmail, Outlook, SendGrid, etc.
- No POC, funciona em modo de log (sem SMTP configurado)

### Por que APScheduler?

- Executa tarefas em background dentro do próprio processo Flask
- Sem necessidade de serviços externos (Celery, Redis)
- Perfeito para o POC — em produção pode migrar para Celery

---

## 5. Modelo de Dados

### Tabela `users`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER PK | Identificador único |
| username | TEXT UNIQUE | Nome de usuário (apto ou nome do porteiro) |
| password_hash | TEXT | Hash seguro da senha (Werkzeug) |
| role | TEXT | 'porteiro' ou 'morador' |
| email | TEXT | E-mail para notificações |
| apartment | TEXT | Número do apartamento (moradores) |

### Tabela `packages`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER PK | Identificador único |
| apartment | TEXT | Apartamento destinatário |
| description | TEXT | Descrição/empresa da encomenda |
| locker | TEXT | Armário de armazenamento |
| arrival_date | TEXT | Data de chegada (ISO 8601) |
| pickup_date | TEXT | Data de retirada (ISO 8601) |
| status | TEXT | 'arrived', 'confirmed', 'picked_up' |
| confirmed_by | TEXT | Nome/apto de quem confirmou digitalmente |
| confirmed_at | TEXT | Data da confirmação digital |
| notified | INTEGER | 1 se o e-mail de chegada foi enviado |
| reminder_sent_at | TEXT | Data do último lembrete enviado |

---

## 6. Segurança

| Aspecto | Antes | Agora |
|---------|-------|-------|
| Senhas | Texto puro | Hash com Werkzeug (pbkdf2:sha256) |
| Autenticação | Nenhuma | Flask-Login com sessões |
| Autorização | Nenhuma | Decoradores por papel (role) |
| CSRF | Nenhuma | Tokens em formulários |
| Debug | Habilitado | Desabilitado por padrão |
| Secret Key | Nenhuma | Configurada e aleatória |

---

## 7. Evolução Futura (Pós-POC)

| Melhoria | Descrição |
|----------|-----------|
| PostgreSQL | Migrar de SQLite para banco mais robusto |
| Celery + Redis | Substituir APScheduler por fila de tarefas |
| API REST | Separar backend e frontend para app mobile |
| Push Notifications | Notificações via app mobile |
| 2FA | Autenticação em dois fatores |
| Assinatura com foto | Morador tira foto da encomenda ao retirar |
| Dashboard administrativo | Para síndico e administradora |
| Docker | Containerização para deploy |
| CI/CD | Pipeline de testes e deploy automático |
