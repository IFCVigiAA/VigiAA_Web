from django.core.management.base import BaseCommand
from django.db import connections, transaction
from casos.models import LogSincronizacao

class Command(BaseCommand):
    help = "Sincroniza TEMP -> OFICIAL (apenas registros novos)"

    def add_arguments(self, parser):
        parser.add_argument('--job_id', type=int, help='ID do LogSincronizacao')

    def handle(self, *args, **options):
        job_id = options.get('job_id')
        
        def atualizar_progresso(pct, msg):
            self.stdout.write(msg)
            if job_id:
                LogSincronizacao.objects.filter(id=job_id).update(progresso=pct, mensagem=msg)

        atualizar_progresso(5, "Iniciando sincronização entre bancos...")

        try:
            with (
                connections["default"].cursor() as cursor_temp,
                transaction.atomic(using="oficial"),
            ):
                with connections["oficial"].cursor() as cursor_ofc:

                    # 1. CASOS POSITIVOS
                    atualizar_progresso(20, "Sincronizando Casos Positivos...")
                    cursor_temp.execute("""
                        SELECT hash_registro, local_atendimento, notificacao, inicio_sintomas, sinan, 
                               data_nasc, bairro, resultado, situacao, observacoes, geometry
                        FROM casos_positivos_temp_gl
                        WHERE hash_registro IS NOT NULL AND geometry IS NOT NULL
                    """)
                    dados_pos = cursor_temp.fetchall()

                    if dados_pos:
                        hashes_pos = [d[0] for d in dados_pos if d[0]]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM casos_positivos WHERE hash_registro = ANY(%s)",
                            [hashes_pos]
                        )
                        existentes_pos = {row[0] for row in cursor_ofc.fetchall()}
                        novos_pos = [d for d in dados_pos if d[0] not in existentes_pos]

                        if novos_pos:
                            cursor_ofc.executemany("""
                                INSERT INTO casos_positivos (
                                    hash_registro, local_atendimento, notificacao, inicio_sintomas, sinan, 
                                    data_nasc, bairro, resultado, situacao, observacoes, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(%s::geometry, 4674))
                            """, novos_pos)

                    # 2. FOCOS AEDES 
                    atualizar_progresso(40, "Sincronizando Focos de Aedes...")
                    cursor_temp.execute("""
                        SELECT hash_registro, n_foco, localidade, imovel, deposito, 
                               tipo_atividade, data_coleta, a_aegypti_form_aquaticas, 
                                a_albopictus_form_aquaticas, geometry
                        FROM focos_aedes_temp
                        WHERE hash_registro IS NOT NULL AND geometry IS NOT NULL
                    """)
                    dados_focos = cursor_temp.fetchall()

                    if dados_focos:
                        hashes_focos = [d[0] for d in dados_focos if d[0]]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM focos_aedes WHERE hash_registro = ANY(%s)",
                            [hashes_focos]
                        )
                        existentes_focos = {row[0] for row in cursor_ofc.fetchall()}
                        novos_focos = [d for d in dados_focos if d[0] not in existentes_focos]

                        if novos_focos:
                            cursor_ofc.executemany("""
                                INSERT INTO focos_aedes (
                                    hash_registro, n_foco, localidade, imovel, deposito, 
                                    tipo_atividade, data_coleta, a_aegypti_form_aquaticas, 
                                    a_albopictus_form_aquaticas, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(%s::geometry, 4674))
                            """, novos_focos)
                        self.stdout.write(
                            f"Focos — total: {len(dados_focos)} | novos: {len(novos_focos)} | ignorados: {len(existentes_focos)}"
                        )

                    # 3. PONTOS ESTRATÉGICOS
                    atualizar_progresso(60, "Sincronizando Pontos Estratégicos...")
                    cursor_temp.execute("""
                        SELECT hash_registro, numero, localidade, endereco, complemento, 
                               data_exame, aegypti_aquaticas, albopictus_aquaticas, geometry
                        FROM pontos_estrategicos_temp
                        WHERE hash_registro IS NOT NULL
                    """)
                    dados_ponto = cursor_temp.fetchall()

                    if dados_ponto:
                        hashes_ponto = [d[0] for d in dados_ponto if d[0]]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM pontos_estrategicos WHERE hash_registro = ANY(%s)",
                            [hashes_ponto]
                        )
                        existentes_ponto = {row[0] for row in cursor_ofc.fetchall()}
                        novos_ponto = [d for d in dados_ponto if d[0] not in existentes_ponto]

                        if novos_ponto:
                            cursor_ofc.executemany("""
                                INSERT INTO pontos_estrategicos (
                                    hash_registro, numero, localidade, endereco, complemento, 
                                    data_exame, aegypti_aquaticas, albopictus_aquaticas, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(%s::geometry, 4674))
                            """, novos_ponto)

                    # 4. ARMADILHAS
                    atualizar_progresso(80, "Sincronizando Armadilhas...")
                    cursor_temp.execute("""
                        SELECT hash_registro, numero, municipio, localidade, endereco, complemento, 
                               quarteiroes, tipo_imovel, tipo_armadilha, geometry
                        FROM relat_arm_temp
                        WHERE hash_registro IS NOT NULL
                    """)
                    dados_arm = cursor_temp.fetchall()

                    if dados_arm:
                        hashes_arm = [d[0] for d in dados_arm if d[0]]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM relat_arm WHERE hash_registro = ANY(%s)",
                            [hashes_arm],
                        )
                        existentes_arm = {row[0] for row in cursor_ofc.fetchall()}
                        novos_arm = [d for d in dados_arm if d[0] not in existentes_arm]

                        if novos_arm:
                            cursor_ofc.executemany(
                                """
                                INSERT INTO relat_arm (
                                    hash_registro, numero, municipio, localidade, endereco, complemento, 
                                    quarteiroes, tipo_imovel, tipo_armadilha, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(%s::geometry, 4674))
                            """,
                                novos_arm,
                            )

                    # 5. OVITRAMPAS
                    atualizar_progresso(95, "Sincronizando Ovitrampas...")
                    cursor_temp.execute("""
                        SELECT hash_registro, id_ovitrampa, endereco, numero, setor_distrito, 
                               quarteirao, data_exame, ovos_aegypti, ovos_albopictus, 
                               outros_ovos, geometry
                        FROM ovitrampas_temp
                        WHERE hash_registro IS NOT NULL
                    """)
                    dados_ovi = cursor_temp.fetchall()

                    if dados_ovi:
                        hashes_ovi = [d[0] for d in dados_ovi if d[0]]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM ovitrampas WHERE hash_registro = ANY(%s)",
                            [hashes_ovi],
                        )
                        existentes_ovi = {row[0] for row in cursor_ofc.fetchall()}
                        novos_ovi = [d for d in dados_ovi if d[0] not in existentes_ovi]

                        if novos_ovi:
                            cursor_ofc.executemany(
                                """
                                INSERT INTO ovitrampas (
                                    hash_registro, id_ovitrampa, endereco, numero, setor_distrito, 
                                    quarteirao, data_exame, ovos_aegypti, ovos_albopictus, 
                                    outros_ovos, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(%s::geometry, 4674))
                            """,
                                novos_ovi,
                            )

            atualizar_progresso(100, "✅ SINCRONIZAÇÃO CONCLUÍDA")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro na sincronização: {str(e)}"))
            raise e