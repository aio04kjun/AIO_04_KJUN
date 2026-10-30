-- 기존 6개 테이블 ERD 기준 / 신규 Supabase 프로젝트용.
-- 실행 순서 및 RPC: ../docs/sql-application.md
-- 동명 테이블을 덮어쓰거나 삭제하지 않습니다. 기존 DB용 마이그레이션이 아닙니다.
BEGIN;

CREATE TABLE public.users (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name varchar(100) NOT NULL CHECK (btrim(name) <> ''),
    phone varchar(30),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(200) NOT NULL CHECK (btrim(name) <> ''),
    description text NOT NULL DEFAULT '',
    price bigint NOT NULL CHECK (price >= 0),
    stock integer NOT NULL DEFAULT 0 CHECK (stock >= 0),
    image_url text,
    is_active boolean NOT NULL DEFAULT true
);
CREATE TABLE public.cart_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    quantity integer NOT NULL CHECK (quantity > 0),
    CONSTRAINT cart_items_user_product_unique UNIQUE (user_id, product_id)
);
CREATE INDEX cart_items_product_idx ON public.cart_items(product_id);
CREATE TABLE public.orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
    status varchar(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'cancelled')),
    total_amount bigint NOT NULL CHECK (total_amount >= 0),
    recipient_name varchar(100) NOT NULL CHECK (btrim(recipient_name) <> ''),
    recipient_phone varchar(30) NOT NULL CHECK (btrim(recipient_phone) <> ''),
    shipping_address text NOT NULL CHECK (btrim(shipping_address) <> ''),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX orders_user_created_idx ON public.orders(user_id, created_at DESC);
CREATE TABLE public.order_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE RESTRICT,
    product_id uuid NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
    product_name varchar(200) NOT NULL CHECK (btrim(product_name) <> ''),
    unit_price bigint NOT NULL CHECK (unit_price >= 0),
    quantity integer NOT NULL CHECK (quantity > 0),
    CONSTRAINT order_items_order_product_unique UNIQUE (order_id, product_id)
);
-- UNIQUE(order_id, product_id)의 인덱스로 주문별 항목 조회도 처리합니다.
CREATE INDEX order_items_product_idx ON public.order_items(product_id);
CREATE TABLE public.payments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL UNIQUE REFERENCES public.orders(id) ON DELETE RESTRICT,
    amount bigint NOT NULL CHECK (amount >= 0),
    status varchar(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'succeeded', 'failed')),
    paid_at timestamptz,
    CONSTRAINT payments_paid_timestamp CHECK (
        (status = 'succeeded' AND paid_at IS NOT NULL)
        OR (status <> 'succeeded' AND paid_at IS NULL)
    )
);

-- 인증 계정과 프로필은 같은 트랜잭션에서 생성합니다.
CREATE FUNCTION public.handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    INSERT INTO public.users(id, name)
    VALUES (NEW.id, left(coalesce(nullif(btrim(NEW.raw_user_meta_data ->> 'name'), ''),
        nullif(split_part(NEW.email, '@', 1), ''), '회원'), 100));
    RETURN NEW;
END;
$$;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
-- 스키마 설치 전에 만들어 둔 인증 계정의 프로필도 생성합니다.
INSERT INTO public.users(id, name)
SELECT id, left(coalesce(nullif(btrim(raw_user_meta_data ->> 'name'), ''),
    nullif(split_part(email, '@', 1), ''), '회원'), 100)
FROM auth.users ON CONFLICT (id) DO NOTHING;

-- 사용자 JWT로 호출합니다. 같은 요청의 재시도에는 같은 p_order_id를 사용합니다.
CREATE FUNCTION public.create_order(
    p_order_id uuid, p_items jsonb, p_recipient_name text,
    p_recipient_phone text, p_shipping_address text, p_expected_total bigint
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_user_id uuid := auth.uid();
    v_items jsonb;
    v_existing_items jsonb;
    v_order public.orders%ROWTYPE;
    v_product public.products%ROWTYPE;
    v_item record;
    v_total bigint := 0;
BEGIN
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'AUTH_REQUIRED' USING ERRCODE = '42501';
    END IF;
    PERFORM 1 FROM public.users WHERE id = v_user_id FOR KEY SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'USER_NOT_FOUND'; END IF;
    IF p_order_id IS NULL OR p_expected_total IS NULL OR p_expected_total < 0
        OR nullif(btrim(p_recipient_name), '') IS NULL
        OR nullif(btrim(p_recipient_phone), '') IS NULL
        OR nullif(btrim(p_shipping_address), '') IS NULL THEN
        RAISE EXCEPTION 'INVALID_ORDER_INPUT';
    END IF;
    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' THEN
        RAISE EXCEPTION 'ITEMS_MUST_BE_ARRAY';
    END IF;
    IF jsonb_array_length(p_items) NOT BETWEEN 1 AND 100 THEN
        RAISE EXCEPTION 'ITEM_COUNT_MUST_BE_1_TO_100';
    END IF;
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_items) AS e(item)
        WHERE jsonb_typeof(item) <> 'object'
           OR jsonb_typeof(item -> 'product_id') IS DISTINCT FROM 'string'
           OR jsonb_typeof(item -> 'quantity') IS DISTINCT FROM 'number'
           OR coalesce(item ->> 'quantity', '') !~ '^[1-9][0-9]*$') THEN
        RAISE EXCEPTION 'INVALID_ITEM';
    END IF;
    -- 중복 상품을 합산하고 UUID 순서로 정렬합니다.
    SELECT jsonb_agg(jsonb_build_object('product_id', product_id, 'quantity', quantity)
        ORDER BY product_id) INTO v_items
    FROM (
        SELECT (item ->> 'product_id')::uuid AS product_id,
            sum((item ->> 'quantity')::integer)::integer AS quantity
        FROM jsonb_array_elements(p_items) AS e(item)
        GROUP BY (item ->> 'product_id')::uuid
    ) AS normalized;

    -- 아직 주문 행이 없어도 동일 주문 ID 요청을 직렬화합니다.
    PERFORM pg_advisory_xact_lock(hashtextextended(p_order_id::text, 0));
    SELECT * INTO v_order FROM public.orders WHERE id = p_order_id FOR UPDATE;
    IF FOUND THEN
        IF v_order.user_id IS DISTINCT FROM v_user_id THEN
            RAISE EXCEPTION 'ORDER_ID_CONFLICT' USING ERRCODE = '42501';
        END IF;
        SELECT jsonb_agg(jsonb_build_object('product_id', product_id, 'quantity', quantity)
            ORDER BY product_id) INTO v_existing_items
        FROM public.order_items WHERE order_id = p_order_id;
        IF v_existing_items IS DISTINCT FROM v_items
            OR v_order.total_amount <> p_expected_total
            OR v_order.recipient_name <> btrim(p_recipient_name)
            OR v_order.recipient_phone <> btrim(p_recipient_phone)
            OR v_order.shipping_address <> btrim(p_shipping_address) THEN
            RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT';
        END IF;
        RETURN to_jsonb(v_order);
    END IF;
    FOR v_item IN SELECT * FROM jsonb_to_recordset(v_items)
        AS x(product_id uuid, quantity integer) ORDER BY product_id LOOP
        SELECT * INTO v_product FROM public.products WHERE id = v_item.product_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCT_NOT_FOUND'; END IF;
        IF NOT v_product.is_active THEN RAISE EXCEPTION 'PRODUCT_INACTIVE'; END IF;
        IF v_product.stock < v_item.quantity THEN RAISE EXCEPTION 'INSUFFICIENT_STOCK'; END IF;
        v_total := v_total + v_product.price * v_item.quantity;
    END LOOP;
    IF v_total <> p_expected_total THEN RAISE EXCEPTION 'PRICE_CHANGED'; END IF;
    INSERT INTO public.orders(id, user_id, total_amount, recipient_name,
        recipient_phone, shipping_address)
    VALUES (p_order_id, v_user_id, v_total, btrim(p_recipient_name),
        btrim(p_recipient_phone), btrim(p_shipping_address)) RETURNING * INTO v_order;
    INSERT INTO public.order_items(order_id, product_id, product_name, unit_price, quantity)
    SELECT p_order_id, p.id, p.name, p.price, x.quantity
    FROM jsonb_to_recordset(v_items) AS x(product_id uuid, quantity integer)
    JOIN public.products p ON p.id = x.product_id;
    RETURN to_jsonb(v_order);
END;
$$;

-- FastAPI 전용 모의 결제. 서버가 검증한 회원 ID를 전달합니다.
-- 실제 PG에는 사용하지 않습니다. 외부 호출을 DB 트랜잭션 안에서 실행하지 마세요.
CREATE FUNCTION public.pay_mock_order(
    p_order_id uuid, p_user_id uuid, p_should_succeed boolean DEFAULT true
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_order public.orders%ROWTYPE;
    v_payment public.payments%ROWTYPE;
    v_item record;
    v_product public.products%ROWTYPE;
    v_failure text;
    v_total numeric;
BEGIN
    IF p_user_id IS NULL OR p_should_succeed IS NULL THEN
        RAISE EXCEPTION 'INVALID_PAYMENT_INPUT';
    END IF;
    PERFORM 1 FROM public.users WHERE id = p_user_id FOR KEY SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'USER_NOT_FOUND'; END IF;
    SELECT * INTO v_order FROM public.orders WHERE id = p_order_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_NOT_FOUND'; END IF;
    IF v_order.user_id IS DISTINCT FROM p_user_id THEN
        RAISE EXCEPTION 'ORDER_FORBIDDEN' USING ERRCODE = '42501';
    END IF;
    IF v_order.status = 'paid' THEN
        SELECT * INTO v_payment FROM public.payments WHERE order_id = p_order_id;
        IF NOT FOUND OR v_payment.status <> 'succeeded'
            OR v_payment.amount <> v_order.total_amount THEN
            RAISE EXCEPTION 'ORDER_PAYMENT_INCONSISTENT';
        END IF;
        RETURN jsonb_build_object('order', to_jsonb(v_order), 'payment', to_jsonb(v_payment));
    END IF;
    IF v_order.status <> 'pending' THEN RAISE EXCEPTION 'ORDER_NOT_PAYABLE'; END IF;
    SELECT sum(unit_price::numeric * quantity) INTO v_total
    FROM public.order_items WHERE order_id = p_order_id;
    IF v_total IS NULL OR v_total <> v_order.total_amount THEN
        RAISE EXCEPTION 'ORDER_TOTAL_MISMATCH';
    END IF;
    IF EXISTS (SELECT 1 FROM public.payments
        WHERE order_id = p_order_id AND status = 'succeeded') THEN
        RAISE EXCEPTION 'ORDER_PAYMENT_INCONSISTENT';
    END IF;
    INSERT INTO public.payments(order_id, amount, status)
    VALUES (p_order_id, v_order.total_amount, 'pending')
    ON CONFLICT (order_id) DO UPDATE
        SET amount = EXCLUDED.amount, status = 'pending', paid_at = NULL;

    -- 전체 상품을 잠그고 검증한 뒤에만 차감합니다.
    FOR v_item IN SELECT product_id, quantity FROM public.order_items
        WHERE order_id = p_order_id ORDER BY product_id LOOP
        SELECT * INTO v_product FROM public.products WHERE id = v_item.product_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCT_NOT_FOUND'; END IF;
        IF NOT v_product.is_active THEN v_failure := 'PRODUCT_INACTIVE';
        ELSIF v_product.stock < v_item.quantity THEN v_failure := 'INSUFFICIENT_STOCK'; END IF;
    END LOOP;
    IF NOT p_should_succeed THEN v_failure := 'MOCK_PAYMENT_DECLINED'; END IF;
    IF v_failure IS NOT NULL THEN
        UPDATE public.payments SET status = 'failed', paid_at = NULL
        WHERE order_id = p_order_id RETURNING * INTO v_payment;
        -- 정상 반환하여 실패 행을 보존합니다. 예외 발생 시 해당 행도 롤백됩니다.
        RETURN jsonb_build_object('order', to_jsonb(v_order),
            'payment', to_jsonb(v_payment), 'failure_code', v_failure);
    END IF;
    UPDATE public.products p SET stock = p.stock - i.quantity
    FROM public.order_items i WHERE i.order_id = p_order_id AND p.id = i.product_id;
    UPDATE public.payments SET status = 'succeeded', paid_at = now()
    WHERE order_id = p_order_id RETURNING * INTO v_payment;
    UPDATE public.orders SET status = 'paid'
    WHERE id = p_order_id RETURNING * INTO v_order;
    RETURN jsonb_build_object('order', to_jsonb(v_order), 'payment', to_jsonb(v_payment));
END;
$$;

CREATE FUNCTION public.cancel_order(p_order_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_order public.orders%ROWTYPE;
BEGIN
    IF auth.uid() IS NULL THEN RAISE EXCEPTION 'AUTH_REQUIRED' USING ERRCODE = '42501'; END IF;
    SELECT * INTO v_order FROM public.orders WHERE id = p_order_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_NOT_FOUND'; END IF;
    IF v_order.user_id IS DISTINCT FROM auth.uid() THEN
        RAISE EXCEPTION 'ORDER_FORBIDDEN' USING ERRCODE = '42501';
    END IF;
    IF v_order.status = 'paid' THEN RAISE EXCEPTION 'PAID_ORDER_CANNOT_CANCEL'; END IF;
    UPDATE public.orders SET status = 'cancelled'
    WHERE id = p_order_id RETURNING * INTO v_order;
    RETURN to_jsonb(v_order);
END;
$$;

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cart_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.users, public.products, public.cart_items,
    public.orders, public.order_items, public.payments FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.products TO anon, authenticated;
GRANT SELECT ON public.users, public.cart_items, public.orders,
    public.order_items, public.payments TO authenticated;
GRANT UPDATE (name, phone) ON public.users TO authenticated;
GRANT INSERT (user_id, product_id, quantity), UPDATE (quantity), DELETE
    ON public.cart_items TO authenticated;
GRANT ALL ON TABLE public.users, public.products, public.cart_items,
    public.orders, public.order_items, public.payments TO service_role;

CREATE POLICY products_public_read ON public.products FOR SELECT
    TO anon, authenticated USING (is_active);
CREATE POLICY users_read_own ON public.users FOR SELECT TO authenticated
    USING (id = (SELECT auth.uid()));
CREATE POLICY users_update_own ON public.users FOR UPDATE TO authenticated
    USING (id = (SELECT auth.uid())) WITH CHECK (id = (SELECT auth.uid()));
CREATE POLICY cart_read_own ON public.cart_items FOR SELECT TO authenticated
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY cart_insert_own ON public.cart_items FOR INSERT TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()) AND EXISTS (
        SELECT 1 FROM public.products p WHERE p.id = product_id AND p.is_active));
CREATE POLICY cart_update_own ON public.cart_items FOR UPDATE TO authenticated
    USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY cart_delete_own ON public.cart_items FOR DELETE TO authenticated
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY orders_read_own ON public.orders FOR SELECT TO authenticated
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY order_items_read_own ON public.order_items FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.orders o
        WHERE o.id = order_id AND o.user_id = (SELECT auth.uid())));
CREATE POLICY payments_read_own ON public.payments FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.orders o
        WHERE o.id = order_id AND o.user_id = (SELECT auth.uid())));

-- SECURITY DEFINER의 기본 PUBLIC 실행 권한을 제거합니다.
REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.create_order(uuid,jsonb,text,text,text,bigint)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.pay_mock_order(uuid,uuid,boolean)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.cancel_order(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_order(uuid,jsonb,text,text,text,bigint) TO authenticated;
GRANT EXECUTE ON FUNCTION public.cancel_order(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.pay_mock_order(uuid,uuid,boolean) TO service_role;
COMMIT;

