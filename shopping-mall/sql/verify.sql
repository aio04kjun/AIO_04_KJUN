-- schema.sql 및 backend-functions.sql 설치 후 개발용 SQL Editor에서 실행합니다.
-- 사전 조건: Supabase Auth에서 테스트 계정 2개 이상 생성(프로필 트리거 확인용).
-- 모든 변경은 마지막 ROLLBACK으로 취소합니다. 오류가 나면 ROLLBACK을 직접 실행하세요.
-- 이 파일은 운영 데이터베이스에서 실행하지 마세요.
BEGIN;

DO $$
DECLARE v_users uuid[];
BEGIN
    SELECT array_agg(id ORDER BY id) INTO v_users
    FROM (SELECT id FROM public.users ORDER BY id LIMIT 2) u;
    IF coalesce(array_length(v_users, 1), 0) < 2 THEN
        RAISE EXCEPTION 'Create two Supabase Auth test accounts first';
    END IF;
    PERFORM set_config('test.user_a', v_users[1]::text, true);
    PERFORM set_config('test.user_b', v_users[2]::text, true);
    PERFORM set_config('test.product', gen_random_uuid()::text, true);
    PERFORM set_config('test.order_a', gen_random_uuid()::text, true);
    PERFORM set_config('test.order_b', gen_random_uuid()::text, true);
    INSERT INTO public.products(id, name, price, stock)
    VALUES (current_setting('test.product')::uuid, '검증용 상품', 12000, 3);
    IF has_function_privilege('authenticated', 'public.pay_mock_order(uuid,uuid,boolean)', 'EXECUTE')
        OR has_function_privilege('anon', 'public.pay_mock_order(uuid,uuid,boolean)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Payment RPC must be server-only';
    END IF;
    IF has_table_privilege('authenticated', 'public.orders', 'INSERT')
        OR has_table_privilege('authenticated', 'public.payments', 'UPDATE') THEN
        RAISE EXCEPTION 'Direct order/payment writes must be denied';
    END IF;
END;
$$;

SELECT set_config('request.jwt.claim.sub', current_setting('test.user_a'), true);
SET LOCAL ROLE authenticated;
DO $$
DECLARE v_items jsonb; v_result jsonb; v_conflict boolean := false;
BEGIN
    v_items := jsonb_build_array(jsonb_build_object(
        'product_id', current_setting('test.product'), 'quantity', 2));
    PERFORM public.add_cart_item(current_setting('test.product')::uuid, 1);
    PERFORM public.add_cart_item(current_setting('test.product')::uuid, 1);
    IF (SELECT quantity FROM public.cart_items
        WHERE product_id = current_setting('test.product')::uuid) <> 2 THEN
        RAISE EXCEPTION 'Repeated add must accumulate quantity';
    END IF;
    v_result := public.create_order(current_setting('test.order_a')::uuid,
        v_items, '테스트 회원', '010-0000-0000', '테스트 주소', 24000);
    IF v_result ->> 'status' <> 'pending' THEN RAISE EXCEPTION 'Expected pending order'; END IF;
    -- 같은 요청은 기존 주문 반환. 별도 행이나 항목을 추가하지 않습니다.
    PERFORM public.create_order(current_setting('test.order_a')::uuid,
        v_items, '테스트 회원', '010-0000-0000', '테스트 주소', 24000);
    BEGIN
        PERFORM public.create_order(current_setting('test.order_a')::uuid,
            v_items, '다른 수령인', '010-0000-0000', '테스트 주소', 24000);
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'IDEMPOTENCY_CONFLICT' THEN RAISE; END IF;
        v_conflict := true;
    END;
    IF NOT v_conflict THEN RAISE EXCEPTION 'Expected idempotency conflict'; END IF;
    IF (SELECT count(*) FROM public.order_items
        WHERE order_id = current_setting('test.order_a')::uuid) <> 1 THEN
        RAISE EXCEPTION 'Retry duplicated order items';
    END IF;
    -- 재고 예약이 없으므로 같은 재고를 보는 두 번째 대기 주문도 생성됩니다.
    PERFORM public.create_order(current_setting('test.order_b')::uuid,
        v_items, '테스트 회원', '010-0000-0000', '테스트 주소', 24000);
END;
$$;
RESET ROLE;

DO $$
DECLARE v_result jsonb; v_payment_id text;
BEGIN
    -- 주문 이후 상품 가격을 변경해도 기존 주문 단가는 유지됩니다.
    UPDATE public.products SET price = 15000 WHERE id = current_setting('test.product')::uuid;
    v_result := public.pay_mock_order(current_setting('test.order_a')::uuid,
        current_setting('test.user_a')::uuid, false);
    IF v_result #>> '{payment,status}' <> 'failed'
        OR (SELECT stock FROM public.products WHERE id = current_setting('test.product')::uuid) <> 3 THEN
        RAISE EXCEPTION 'Failed payment changed stock';
    END IF;
    v_payment_id := v_result #>> '{payment,id}';
    v_result := public.pay_mock_order(current_setting('test.order_a')::uuid,
        current_setting('test.user_a')::uuid, true);
    IF v_result #>> '{payment,status}' <> 'succeeded'
        OR v_result #>> '{order,status}' <> 'paid'
        OR v_result #>> '{payment,id}' <> v_payment_id
        OR (v_result #>> '{payment,amount}')::bigint <> 24000 THEN
        RAISE EXCEPTION 'Payment retry/snapshot mismatch';
    END IF;
    PERFORM public.pay_mock_order(current_setting('test.order_a')::uuid,
        current_setting('test.user_a')::uuid, true);
    IF (SELECT stock FROM public.products WHERE id = current_setting('test.product')::uuid) <> 1 THEN
        RAISE EXCEPTION 'Duplicate payment deducted stock twice';
    END IF;
    IF (SELECT count(*) FROM public.payments WHERE order_id = current_setting('test.order_a')::uuid) <> 1 THEN
        RAISE EXCEPTION 'Payment retry created a second row';
    END IF;
    v_result := public.pay_mock_order(current_setting('test.order_b')::uuid,
        current_setting('test.user_a')::uuid, true);
    IF v_result ->> 'failure_code' <> 'INSUFFICIENT_STOCK'
        OR v_result #>> '{order,status}' <> 'pending'
        OR (SELECT stock FROM public.products WHERE id = current_setting('test.product')::uuid) <> 1 THEN
        RAISE EXCEPTION 'Out-of-stock payment should fail without deduction';
    END IF;
END;
$$;

SELECT set_config('request.jwt.claim.sub', current_setting('test.user_b'), true);
SET LOCAL ROLE authenticated;
DO $$
DECLARE v_denied boolean := false;
BEGIN
    IF EXISTS (SELECT 1 FROM public.orders WHERE id = current_setting('test.order_a')::uuid)
        OR EXISTS (SELECT 1 FROM public.order_items WHERE order_id = current_setting('test.order_a')::uuid)
        OR EXISTS (SELECT 1 FROM public.payments WHERE order_id = current_setting('test.order_a')::uuid)
        OR EXISTS (SELECT 1 FROM public.cart_items WHERE user_id = current_setting('test.user_a')::uuid) THEN
        RAISE EXCEPTION 'RLS exposed another user data';
    END IF;
    BEGIN
        PERFORM public.cancel_order(current_setting('test.order_b')::uuid);
    EXCEPTION WHEN insufficient_privilege THEN v_denied := true;
    END;
    IF NOT v_denied THEN RAISE EXCEPTION 'Another user cancelled the order'; END IF;
END;
$$;
RESET ROLE;

SELECT set_config('request.jwt.claim.sub', current_setting('test.user_a'), true);
SET LOCAL ROLE authenticated;
DO $$
DECLARE v_result jsonb;
BEGIN
    v_result := public.cancel_order(current_setting('test.order_b')::uuid);
    IF v_result ->> 'status' <> 'cancelled' THEN RAISE EXCEPTION 'Cancellation failed'; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.cart_items
        WHERE product_id = current_setting('test.product')::uuid) THEN
        RAISE EXCEPTION 'Checkout should preserve cart';
    END IF;
END;
$$;
RESET ROLE;
SELECT 'PASS: order retry, snapshot, failed payment, successful retry, stock, RLS, cancel, cart' AS result;
ROLLBACK;
